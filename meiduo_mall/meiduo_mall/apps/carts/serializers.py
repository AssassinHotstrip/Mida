from rest_framework import serializers

from goods.models import SKU


class CartSerializer(serializers.Serializer):
    """购物车 保存/修改 序列化器"""
    sku_id = serializers.IntegerField(label='商品ID', min_value=1)
    count = serializers.IntegerField(label='商品数量', min_value=1)
    selected = serializers.BooleanField(label='是否勾选', default=True)

    def validate_sku_id(self, value):
        """对商品ID追加额外的校验逻辑"""
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('sku_id 不存在')

        return value


class CartSKUSerializer(serializers.ModelSerializer):
    """序列化输出商品模型"""
    count = serializers.IntegerField(label='商品数量')
    selected = serializers.BooleanField(label='是否勾选')

    class Meta:
        model = SKU
        fields = ['id', 'name', 'count', 'price', 'default_image_url', 'selected']


class CartSelectAllSerializer(serializers.Serializer):
    """
    购物车全选
    """
    selected = serializers.BooleanField(label='全选')


class CartDeleteSeriazlier(serializers.Serializer):
    """删除购物车的序列化器"""
    sku_id = serializers.IntegerField(label='商品ID', min_value=1)

    def validate_sku_id(self, value):
        """对商品ID追加额外的校验逻辑"""
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError('sku_id 不存在')

        return value