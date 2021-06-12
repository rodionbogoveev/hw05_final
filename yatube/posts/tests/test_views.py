import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        cls.user = User.objects.create(username='rodion')
        cls.group = Group.objects.create(
            title='Название',
            slug='test_slug',
            description='Описание',
        )
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
        cls.post = Post.objects.create(
            text='Текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )
        cls.another_group = Group.objects.create(
            title='Другое название',
            slug='test_another_slug',
            description='Другое описание',
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        return super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = (
            ('posts/index.html', reverse('index')),
            ('posts/group.html', (
                reverse('group_posts', kwargs={'slug': 'test_slug'}))),
            ('posts/new_post.html', reverse('new_post')),
        )
        for template, reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('index'))
        post = response.context['page'].object_list[0]
        PostsViewTests.post_context(self, post)

    def test_group_posts_page_show_correct_context(self):
        """Шаблон group_posts сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('group_posts', kwargs={'slug': 'test_slug'}))
        post = response.context['page'].object_list[0]
        group = response.context['group']
        PostsViewTests.post_context(self, post)
        PostsViewTests.group_context(self, group)

    def test_new_post_page_shows_correct_context(self):
        """Шаблон new_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('new_post'))
        form_fields = (
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
            ('image', forms.fields.ImageField),
        )
        for value, expected in form_fields:
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_shows_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('post_edit', kwargs={'username': 'rodion', 'post_id': 1}))
        form_fields = (
            ('text', forms.fields.CharField),
            ('group', forms.fields.ChoiceField),
            ('image', forms.fields.ImageField),
        )
        for value, expected in form_fields:
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('profile', kwargs={'username': 'rodion'}))
        post = response.context['page'].object_list[0]
        author = response.context['author']
        PostsViewTests.post_context(self, post)
        PostsViewTests.author_context(self, author)

    def test_post_page_show_correct_context(self):
        """Шаблон post сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('post', kwargs={'username': 'rodion', 'post_id': 1}))
        post = response.context['post']
        author = response.context['author']
        paginator = response.context['paginator'].count
        count = Post.objects.all().count()
        PostsViewTests.post_context(self, post)
        PostsViewTests.author_context(self, author)
        self.assertEqual(paginator, count)

    def test_new_group_post_shows_at_index_and_group_pages(self):
        """При создании поста с указанием группы, этот пост появляется
        на главной странице сайта и на странице выбранной группы."""
        pages = (
            (reverse('index')),
            (reverse('group_posts', kwargs={'slug': 'test_slug'}))
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.guest_client.get(page).context['page']
                self.assertIn(self.post, response)

    def test_new_group_post_not_shows_at_another_group_page(self):
        """При создании поста с указанием группы, этот пост не попал в группу,
        которая не была указана."""
        response = self.guest_client.get(reverse(
            'group_posts',
            kwargs={'slug': 'test_another_slug'})).context['page']
        self.assertNotIn(self.post, response)

    def test_index_page_cache_works_correctly(self):
        """Кэширование главной страницы работает корректно."""
        response_one = self.guest_client.get(reverse('index')).content
        Post.objects.create(
            text='Другой текст',
            author=self.user,
            group=self.group,
            image=self.uploaded
        )
        response_second = self.guest_client.get(reverse('index')).content
        cache.clear()
        response_three = self.guest_client.get(reverse('index')).content
        self.assertEqual(response_one, response_second)
        self.assertNotEqual(response_second, response_three)

    def post_context(self, post):
        self.assertEqual(post, self.post)
        self.assertEqual(post.text, 'Текст')
        self.assertEqual(post.author.username, 'rodion')
        self.assertEqual(post.group.slug, 'test_slug')
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.image, self.post.image)

    def group_context(self, group):
        self.assertEqual(group, self.group)
        self.assertEqual(group.title, 'Название')
        self.assertEqual(group.slug, 'test_slug')
        self.assertEqual(group.description, 'Описание')

    def author_context(self, author):
        self.assertEqual(author.username, 'rodion')


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='rodion')
        cls.group = Group.objects.create(
            title='Название',
            slug='test_slug',
            description='Описание',
        )
        for i in range(13):
            Post.objects.create(
                text=f'Пост {i}',
                author=cls.user,
                group=cls.group
            )

    def test_first_page_contains_ten_records(self):
        """Paginator передает на первую страницу 10 записей."""
        pages = (
            (reverse('index')),
            (reverse('group_posts', kwargs={'slug': 'test_slug'})),
            (reverse('profile', kwargs={'username': 'rodion'}))
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                len_page = len(response.context['page'].object_list)
                self.assertEqual(len_page, 10)

    def test_second_page_contains_three_records(self):
        """Paginator передает на вторую страницу 3 записи."""
        pages = (
            (reverse('index') + '?page=2'),
            (reverse('group_posts', kwargs={'slug': 'test_slug'}) + '?page=2'),
            (reverse('profile', kwargs={'username': 'rodion'}) + '?page=2')
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                len_page = len(response.context['page'].object_list)
                self.assertEqual(len_page, 3)
