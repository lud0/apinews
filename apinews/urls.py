from main.views import NewsList, CategoriesList
from django.urls import path

urlpatterns = [
    path('api/v1/news', NewsList.as_view(), name='news'),
    path('api/v1/categories', CategoriesList.as_view(), name='categories'),
]
