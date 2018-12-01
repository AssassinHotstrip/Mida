from django.shortcuts import render
from drf_haystack.viewsets import HaystackViewSet
from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter


from .models import SKU
from .serializers import SKUSerializer, SKUIndexSerializer


# Create your views here.
# GET /categories/(?P<category_id>\d+)/skus?page=xxx&page_size=xxx&ordering=xxx
class SKUListView(ListAPIView):
    """商品列表视图"""

    # 指定排序的后端面
    filter_backends = [OrderingFilter]
    ordering_fields = ('create_time', 'price', 'sales')



    # 指定查询集
    # queryset = SKU.objects.all()
    def get_queryset(self):
        # 提取出url路径中的正则组的关键字参数
        category_id = self.kwargs.get('category_id')
        return SKU.objects.filter(category_id=category_id, is_launched=True)

    # 指定序列化器
    serializer_class = SKUSerializer


class SKUSearchViewSet(HaystackViewSet):
    """SKU搜索"""
    index_models = [SKU]

    serializer_class = SKUIndexSerializer