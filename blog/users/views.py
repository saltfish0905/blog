from django.shortcuts import render

# Create your views here.
#注册视图
from django.views import View
from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse, JsonResponse

class RegisterView(View):

    def get(self,request):

        return render(request,'register.html')

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


