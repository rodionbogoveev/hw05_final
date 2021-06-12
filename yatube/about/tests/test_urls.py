from http import HTTPStatus

from django.test import Client, TestCase
from django.urls.base import reverse


class AboutURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_url_available_for_any_user(self):
        """Адрес доступен для любого пользователя."""
        urls = ['/about/author/', '/about/tech/']
        for url in urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_accessible_by_name(self):
        """URL, генерируемый при помощи имени, доступен."""
        url_names = ['about:author', 'about:tech']
        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(reverse(url))
                self.assertEqual(response.status_code, HTTPStatus.OK)
