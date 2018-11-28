from django.conf.urls import url

from . import views

urlpatterns = [
    # 返回QQ扫码url
    url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
    # qq OAuth2.0认证
    url(r'^qq/users/$', views.QQAuthUserView.as_view()),
]