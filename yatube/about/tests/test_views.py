from django.test import Client, TestCase
from django.urls import reverse


class AboutViewTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_page_uses_correct_template(self):
        """При запросе по имени вызывается ожидаемый шаблон."""
        url_names_templates = {
            'about:author': 'about/author.html',
            'about:tech': 'about/tech.html',
        }
        for url, template in url_names_templates.items():
            with self.subTest(url=url):
                response = self.guest_client.get(reverse(url))
                self.assertTemplateUsed(response, template)

    def test_url_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        urls_templates = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for url, template in urls_templates.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)
