from rest_framework import serializers

from .models import Area

class AreaSerializer(serializers.ModelSerializer):
    """序列化省份数据"""

    class Meta:
        model = Area
        fields = ['id', 'name']



class SubsAreaSerializer(serializers.ModelSerializer):
    """序列化市区数据"""
    subs = AreaSerializer(many=True, read_only=True)

    class Meta:
        model = Area
        fields = ['id', 'name', 'subs']

