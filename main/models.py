from django.db import models
from django.forms import ModelForm
from rest_framework import serializers


class News(models.Model):
    """Schema model for the News object. Searched fields are db indexes. A uniqueness constraint is enforced."""

    category = models.CharField(max_length=100, db_index=True)
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=500)

    url = models.URLField(max_length=1024)
    content = models.TextField(null=True)

    class Meta:
        unique_together = ['category', 'date', 'name']


class NewsSerializer(serializers.ModelSerializer):
    """Serializer used to expose content via API"""
    class Meta:
        model = News
        fields = ('id', 'category', 'date', 'name', 'url', 'content')


class CategorySerializer(serializers.Serializer):
    """Serializer used to expose content via API"""
    category = serializers.CharField()
    count = serializers.IntegerField()


class NewsForm(ModelForm):
    """Form used to validate external data before db insertion"""
    class Meta:
        model = News
        fields = ('category', 'date', 'name', 'url', 'content')
