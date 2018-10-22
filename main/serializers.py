from rest_framework import serializers
class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ('id', 'title', 'code', 'linenos', 'language', 'style')