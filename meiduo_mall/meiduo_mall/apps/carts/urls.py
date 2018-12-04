from django.conf.urls import url

from . import views


urlpatterns = [
    # 购物车:增删改查
    url(r'^carts/$', views.CartView.as_view()),

    url(r'^carts/selection/$', views.CartSelectAllView.as_view()),
]