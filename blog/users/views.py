from django.shortcuts import render

# Create your views here.
#注册视图
from django.views import View
from django.http.response import HttpResponseBadRequest
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.http import HttpResponse

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

        
