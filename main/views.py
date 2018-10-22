from datetime import datetime

from django.db.models import Count
from django.db.models import Q
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .models import News, NewsSerializer, CategorySerializer


class NewsList(GenericAPIView):
    """
    List all news.

    Supports the following query parameters:
    `q=<search query>` to filter news containing the term <search query> (case insensitive)
    `daterange=<start_date>-<end_date>` to filter news by published date range, where the date format is YYYYMMDD
    `category=<category>` to filter news within a given category, for a list of available categories use the `api/v1/categories` endpoint

    NB: this class is a subclass of GenericAPIView to inherit pagination code
    """

    def get_queryset(self):
        return News.objects.all()

    def get(self, request):
        """
        Returns the paginated list of news according to the parameter filters if present
        """
        filters = self.get_filters(request.GET)
        news = self.get_queryset().filter(filters)

        # paginate the queryset
        page = self.paginate_queryset(news)
        if page is not None:
            serializer = NewsSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = NewsSerializer(news, many=True)
        return Response(serializer.data)

    @staticmethod
    def get_filters(params):
        """
        Converts the GET parameters into queryset filters:
        ?q=<string>&daterange=YYYYMMDD-YYYYMMDD&category=<string>
        """

        filters = Q()
        if 'q' in params:
            filters &= (Q(name__icontains=params['q']) | Q(content__icontains=params['q']))

        if 'daterange' in params:
            try:
                start, end = params['daterange'].split("-")
                start_date = datetime.strptime(start, "%Y%m%d").date()
                end_date = datetime.strptime(end, "%Y%m%d").date()
            except:
                # ignores bad formed date formats
                pass
            else:
                if start_date <= end_date:
                    filters &= Q(date__gte=start_date) & Q(date__lte=end_date)

        if 'category' in params:
            filters &= Q(category=params['category'])

        return filters


class CategoriesList(GenericAPIView):
    """
    List all categories for which there are news.

    NB: this class is a subclass of GenericAPIView to inherit pagination code
    """

    def get_queryset(self):
        return News.objects.values('category').annotate(count=Count('pk'))

    def get(self, request):
        """
        Returns the paginated list of categories and their counting
        """
        categories = self.get_queryset()

        # paginate the queryset
        page = self.paginate_queryset(categories)
        if page is not None:
            serializer = CategorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)
