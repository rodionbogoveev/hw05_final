import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from ..models import Group, Post

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create(username='rodion')
        cls.group = Group.objects.create(
            title='Название',
            slug='test-slug',
            description='Описание',
        )
        cls.post = Post.objects.create(
            text='Текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )
        cls.another_user = User.objects.create(username='rick_astley')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        return super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_another_client = Client()
        self.authorized_another_client.force_login(self.another_user)

    def test_url_is_available_the_users_access_rights(self):
        """Страница доступна в соответствии с правами доступа пользователя."""
        clients_urls = (
            (self.guest_client, '/'),
            (self.guest_client, '/group/test-slug/'),
            (self.authorized_client, '/new/'),
            (self.guest_client, '/rodion/'),
            (self.guest_client, '/rodion/1/')
        )
        for client, url in clients_urls:
            with self.subTest(client=client):
                response = client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_non_existent_url_returns_404(self):
        """Страница 404 доступна."""
        response = self.guest_client.get('/f3@1/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        urls_templates = (
            ('/', 'posts/index.html'),
            ('/group/test-slug/', 'posts/group.html'),
            ('/new/', 'posts/new_post.html')
        )
        for url, template in urls_templates:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_post_edit_url_available_only_for_post_author(self):
        """Страница post_edit доступна только для автора поста."""
        url = '/rodion/1/edit/'
        users_status_code = {
            self.guest_client: HTTPStatus.FOUND,
            self.authorized_client: HTTPStatus.OK,
            self.authorized_another_client: HTTPStatus.FOUND
        }
        for users, status_code in users_status_code.items():
            with self.subTest(users=users):
                get_user_status_code = users.get(url).status_code
                self.assertEqual(get_user_status_code, status_code)

    def test_post_edit_url_uses_correct_template(self):
        """Страница post_edit использует корректный шаблон."""
        url = '/rodion/1/edit/'
        template = 'posts/new_post.html'
        response = self.authorized_client.get(url)
        self.assertTemplateUsed(response, template)

    def test_post_edit_url_redirect_anonymous_on_login(self):
        """Страница post_edit перенаправит пользователя на
        ожидаемую страницу."""
        items = (
            (self.guest_client,
             '/rodion/1/edit/', '/auth/login/?next=/rodion/1/edit/'),
            (self.authorized_another_client, '/rodion/1/edit/', '/rodion/1/')
        )
        for client, url, redirect_url in items:
            with self.subTest(client=client, url=url):
                response = client.get(url)
                self.assertRedirects(response, redirect_url)
