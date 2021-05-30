#进行users子应用的视图路由
from django.urls import path
from users.views import ImageCodeView, RegisterView
urlpatterns=[
    #path第一个参数为路由,第二个参数为视图函数名
    path('register/',RegisterView.as_view(),name='register'),

    #图片验证码路由
    path('imagecode/',ImageCodeView.as_view(),name='imagecode')
]