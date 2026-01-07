from rest_framework import serializers


class PerformanceSerializer(serializers.Serializer):
    period = serializers.CharField()
    change = serializers.FloatField()


class RegionPerformanceSerializer(serializers.Serializer):
    name = serializers.CharField()
    price = serializers.FloatField()
    performance = PerformanceSerializer(many=True)


class ProductPerformanceSerializer(serializers.Serializer):
    name = serializers.CharField()
    price = serializers.FloatField()
    prevPrice = serializers.FloatField()
    performance = PerformanceSerializer(many=True)
    regions = RegionPerformanceSerializer(many=True)
