#进行users子应用的视图路由
from django.urls import path
from users.views import ImageCodeView, RegisterView
from users.views import SmsCodeView
urlpatterns=[
    #path第一个参数为路由,第二个参数为视图函数名
    path('register/',RegisterView.as_view(),name='register'),

    #图片验证码路由
    path('imagecode/',ImageCodeView.as_view(),name='imagecode'),
    
    #短信发送
    path('smscode/',SmsCodeView.as_view(),name='smscode'),
    ]