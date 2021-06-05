from django.shortcuts import render
from django.shortcuts import redirect
from django.urls import reverse
# Create your views here.
#注册视图
from django.views import View
from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse, JsonResponse, response
import re
from users.models import User
from django.db import DatabaseError

class RegisterView(View):

    def get(self,request):

        return render(request,'register.html')
    def post(self,request):
        '''
        1.接受数据
        2.验证数据
            2.1参数是否齐全
            2.2手机号格式是否正确
            2.3密码是否符合格式
            2.4密码和确认密码要一致
            2.5短信验证码是否和redis中的一致
        3.保存注册信息
        4.返回响应跳转到指定页面
        '''

        #1
        mobile=request.POST.get('mobile')
        password=request.POST.get('password')
        password2=request.POST.get('password2')
        smscode=request.POST.get('sms_code')
        #2.1
        if not all([mobile,password,password2,smscode]):
            return HttpResponseBadRequest('缺少必要的参数')
        #2.2
        if not re.match(r'^1[3-9]\d{9}$',mobile):
           return HttpResponseBadRequest('手机号不符合规则')
        #2.3
        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):
            return HttpResponseBadRequest('请输入8-20位密码，密码是数字和字母')
        #2.4
        if password!=password2:
            return HttpResponseBadRequest('两次密码不一致')
        #2.5
        redis_conn=get_redis_connection('default')
        redis_sms_code=redis_conn.get('sms:%s'%mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode!=redis_sms_code.decode():
            return HttpResponseBadRequest('短信验证码不一致')
        #3 create_user使用系统方法对密码进行加密
        try:
            user=User.objects.create_user(username=mobile,mobile=mobile,password=password)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')
        
        from django.contrib.auth import login
        login(request,user)
        #4 暂时先返回注册成功信息，后面再补充跳转到指定页面
        # redirect 重定向 reverse通过namespace:name来获取到视图所对应的路由
        response=redirect(reverse('home:index'))
        #设置cookie信息，以方便首页中用户信息展示的判断和用户信息的展示
        response.set_cookie('is_login',True)
        response.set_cookie('username',user.username,max_age=7*24*3600)
        return response

class ImageCodeView(View):

    def get(self,request):
        '''
        1.接受前端传递的uuid
        2.判断uuid是否获取
        3.通过调用captcha生成图片验证码（图片二进制和图片内容）
        4.将图片内容保存到redis中 
            uuid作为一个key,图片内容作为一个value 同时还需要设置一个时效
        5.返回图片二进制
        '''
        #1
        uuid=request.GET.get('uuid')
        #uuid='img_'+uuid
        #2
        if uuid is None:
            return HttpResponseBadRequest('没有传递uuid')
        #3
        text,image=captcha.generate_captcha()
        #4
        redis_conn=get_redis_connection('default')
        #key设置为uuid,seconds设置为过期秒数 300秒，value为图片二进制内容
        redis_conn.setex('img:%s'%uuid,300,text)
        #5
        return HttpResponse(image,content_type='image/jpeg')

from django.http.response import JsonResponse
from utils.response_code import RETCODE
import logging
logger=logging.getLogger('django')
from random import randint
from libs.yuntongxun.sms import CCP

class SmsCodeView(View):
    def get(self,request):
        '''
        1.接受参数
        2.参数的验证
            2.1验证参数是否齐全
            2.2图片验证码的验证
                连接redis获取其中的图片验证码
                判断图片验证码是否存在
                如果图片验证码未过期，获取到之后就可以删除图片验证码
                比对图片验证码
        3.生成短信验证码
        4.保存短信验证码到redis中
        5.发送短信
        6.返回响应
        '''
        #1
        mobile=request.GET.get('mobile')
        image_code=request.GET.get('image_code')
        uuid=request.GET.get('uuid')
        #2.1
        if not all ([mobile,image_code,uuid]):
            return JsonResponse({'code':RETCODE.NECESSARYPARAMERR,'errmsg':'缺少必要的参数'})
        #2.2
        redis_conn=get_redis_connection('default')
        redis_image_code=redis_conn.get('img:%s'%uuid)
        if redis_image_code is None:
            return JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图片验证码已过期'})
        '''
        try:
            redis_conn.delete('img:%s'%uuid)
        except Exception as e:
            logger.error(e)
        if redis_image_code.decode().lower() !=image_code.lower():
            return JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图片验证码错误'})
        '''    
        try:
            redis_conn.delete('img:%s'%uuid)
        except Exception as e:
            logger.error(e)
        #         比对图片验证码, 注意大小写的问题， redis的数据是bytes类型
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code':RETCODE.IMAGECODEERR,'errmsg':'图片验证码错误'})
        
        #3
        sms_code='%06d'%randint(0,999999)
        #为了后期比对方便，将短信验证码记录到日志中
        logger.info(sms_code)
        #4
        redis_conn.setex('sms:%s'%mobile,300,sms_code)
        #5  
            #参数1 测试手机号
            #参数2 一个列表 您的验证码是{1},请于{2}分钟内正确输入，1短信验证码，2短信验证码有效期
            #参数3 模板id
        CCP().send_template_sms(mobile,[sms_code,5],1)
        #6
        return JsonResponse({'code':RETCODE.OK,'errmsg':'短信发送成功'})

class LoginView(View):
    def get(self,request):
        
        return render(request,'login.html')
    def post(self,request):
        '''
        1.接收参数
        2.参数验证
            2.1验证手机号是否符合规则
            2.2验证密码是否符合规则
        3.用户认证登录
        4.状态保持
        5.根据用户选择的是否记住登录状态进行判断
        6.为了首页显示设置cookie信息
        7.返回响应
        '''
        #1
        mobile=request.POST.get('mobile')
        password=request.POST.get('password')
        remember=request.POST.get('remember')
        #2
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        if not re.match(r'^[0-9A-Za-z]{8,20}$',password):
            return HttpResponseBadRequest('密码不符合规则')
        #3 采用系统自带的认证方法
        # 若用户名和密码正确，会返回user,不正确会返回None
        from django.contrib.auth import authenticate
        #默认认证方法针对username字段进行用户名判断
        #当前判断信息为手机号，需要修改一下认证字段,需要到user模型中进行修改
        user=authenticate(mobile=mobile,password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')
        #4
        from django.contrib.auth import login
        login(request,user)
        #5/6
        response=redirect(reverse('home:index'))
        if remember !='on':
            request.session.set_expiry(0)
            response.set_cookie('is_login',True)
            response.set_cookie('username',user.username,max_age=14*24*3600)
        else:
            request.session.set_expiry(None) #默认为两周
            response.set_cookie('is_login',True,max_age=14*24*3600)
            response.set_cookie('username',user.username,max_age=14*24*3600)
        return response

from django.contrib.auth import logout       
class LogoutView(View):
    
    def get(self,request):
        #1.session数据清除
        logout(request)
        #2.删除部分cookie数据
        response=redirect(reverse('home:index'))
        response.delete_cookie('is_login')
        #3.跳转到首页
        return response
