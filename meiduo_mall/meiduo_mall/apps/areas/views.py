from django.shortcuts import render
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Area
from .serializers import AreaSerializer,SubsAreaSerializer

# Create your views here.
class AreasViewSet(ReadOnlyModelViewSet):
    """返回省市区数据"""
    pagination_class = None  # 关闭分页(重要)
    # 指定查询集
    # queryset = Area.objects.all()重写返回指定查询集
    def get_queryset(self):
       if self.action == 'list':  # 如果是list行为，表示要获取省份信息
           return Area.objects.filter(parent=None)
       else:
           return Area.objects.all()

    # 指定序列化器
    # serializer_class = AreaSerializer
    # 重写以返回指定的序列化器（省/市/区）
    def get_serializer_class(self):
        if self.action == 'list':
            return  AreaSerializer
        else:
            return SubsAreaSerializer