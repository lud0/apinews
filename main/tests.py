from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import News


class NewsAPITests(APITestCase):

    def setUp(self):
        """
        Creates a News entry for testing the API parameter filterings
        """
        self.url = reverse('news')
        news = News.objects.create(**{'name': 'A quantum leap toward expanding the search for dark matter',
                                      'category': 'ScienceAndTechnology',
                                      'date': '2018-09-25',
                                      'url': 'https://phys.org/news/2018-09-quantum-dark.html',
                                      'content': 'Unraveling the Quantum Structure of Quantum Chromodynamics',})
        self.news = news

    def assess_identical(self, response):
        jresp = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key, value in self.news.__dict__.items():
            if key != '_state':
                self.assertEqual(jresp['results'][0][key], value)

    def assess_no_results(self, response):
        jresp = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {'count': 0, 'next': None, 'previous': None, 'results': []}
        for key, value in expected_response.items():
            self.assertEqual(jresp[key], value)

    def test_get_news(self):
        response = self.client.get(self.url, format='json')
        self.assess_identical(response)

    def test_filter_q_news(self):
        response = self.client.get(self.url, data={'q': 'quantum'}, format='json')
        self.assess_identical(response)
        response = self.client.get(self.url, data={'q': 'unicorn'}, format='json')
        self.assess_no_results(response)

    def test_filter_daterange_news(self):
        response = self.client.get(self.url, data={'daterange': '20180825-20180925'}, format='json')
        self.assess_identical(response)
        response = self.client.get(self.url, data={'daterange': '20180825-20180920'}, format='json')
        self.assess_no_results(response)

    def test_filter_category_news(self):
        response = self.client.get(self.url, data={'category': 'ScienceAndTechnology'}, format='json')
        self.assess_identical(response)
        response = self.client.get(self.url, data={'category': 'mythological_creatures'}, format='json')
        self.assess_no_results(response)


class NewsCategoriesAPITests(APITestCase):

    def setUp(self):
        """
        Creates a News entry for testing the API categories
        """
        self.url = reverse('categories')
        news = News.objects.create(**{'name': 'A quantum leap toward expanding the search for dark matter',
                                      'category': 'ScienceAndTechnology',
                                      'date': '2018-09-25',
                                      'url': 'https://phys.org/news/2018-09-quantum-dark.html',
                                      'content': 'Unraveling the Quantum Structure of Quantum Chromodynamics', })
        self.news = news

    def test_get_categories(self):
        response = self.client.get(self.url, format='json')
        jresp = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(jresp['results'][0]['category'], self.news.category)
        self.assertEqual(jresp['results'][0]['count'], 1)
