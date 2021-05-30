from django.shortcuts import render

# Create your views here.
#注册视图
from django.views import View
from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse, JsonResponse
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
        #if not re.match(r'^1[3-9]\d{9}$',mobile):
        #   return HttpResponseBadRequest('手机号不符合规则')
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
        #4 暂时先返回注册成功信息，后面再补充跳转到指定页面
        return HttpResponse('注册成功,重定向到首页')

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


