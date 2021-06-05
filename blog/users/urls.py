#进行users子应用的视图路由
from django.urls import path
from users.views import ImageCodeView, LoginView, RegisterView
from users.views import SmsCodeView
from users.views import LogoutView
urlpatterns=[
    #path第一个参数为路由,第二个参数为视图函数名
    path('register/',RegisterView.as_view(),name='register'),

    #图片验证码路由
    path('imagecode/',ImageCodeView.as_view(),name='imagecode'),

    
    #短信发送
    path('smscode/',SmsCodeView.as_view(),name='smscode'),

    #登陆路由
    path('login/',LoginView.as_view(),name='login'),

    #退出登录
    path('logout/',LogoutView.as_view(),name='logout'),
    ]