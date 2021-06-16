import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PostsViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        cls.user = User.objects.create(username='rodion')
        cls.author = User.objects.create(username='dicaprio')
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
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

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
        content = self.guest_client.get(reverse('index')).content
        Post.objects.create(
            text='Другой текст',
            author=self.user,
            group=self.group,
            image=self.uploaded
        )
        cached_content = self.guest_client.get(reverse('index')).content
        cache.clear()
        refresh_content = self.guest_client.get(reverse('index')).content
        self.assertEqual(content, cached_content)
        self.assertNotEqual(cached_content, refresh_content)

    def test_auth_user_can_follow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей."""
        get_follow = PostsViewTests.user_follows_author(self)
        self.assertTrue(get_follow)

    def test_not_auth_user_can_follow(self):
        """Авторизованный пользователь может удалять
        других пользователей из подписок."""
        Follow.objects.create(
            user=self.user, author=self.author)
        self.authorized_client.get(reverse(
            'profile_unfollow',
            kwargs={'username': self.author.username}))
        get_follow = Follow.objects.filter(
            user=self.user, author=self.author).exists()
        self.assertFalse(get_follow)

    def test_post_is_visible_for_follower(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан."""
        PostsViewTests.user_follows_author(self)
        author_post = PostsViewTests.author_creates_post(self)
        response = self.authorized_client.get(
            reverse('follow_index')).context['page']
        self.assertIn(author_post, response)

    def test_post_is_not_visible_for_not_follower(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто на него не подписан."""
        PostsViewTests.user_follows_author(self)
        author_post = PostsViewTests.author_creates_post(self)
        another_user = User.objects.create(username='another_user')
        self.another_user = Client()
        self.another_user.force_login(another_user)
        response = self.another_user.get(
            reverse('follow_index')).context['page']
        self.assertNotIn(author_post, response)

    def user_follows_author(self):
        """Пользователь подписывается на автора."""
        self.authorized_client.get(reverse(
            'profile_follow',
            kwargs={'username': self.author.username}))
        get_follow = Follow.objects.filter(
            user=self.user, author=self.author)
        return get_follow

    def author_creates_post(self):
        """Автор создает пост."""
        author_post = Post.objects.create(
            text='Я - Леонардо Ди Каприо',
            author=self.author
        )
        return author_post

    def test_authorized_user_can_comment_post(self):
        """Авторизованный пользователь может комментировать пост."""
        form_data = {'text': 'Комментарий'}
        self.authorized_client.post(
            reverse('add_comment', kwargs={
                'username': self.user.username,
                'post_id': self.post.id}),
            data=form_data,
            follow=True)
        get_comment = Comment.objects.filter(post=self.post, author=self.user,
                                             text='Комментарий')
        self.assertTrue(get_comment)

    def test_non_authorized_user_cannot_comment_post(self):
        """Неавторизованный пользователь не может комментировать пост."""
        form_data = {'text': 'Другой комментарий'}
        self.guest_client.post(
            reverse('add_comment', kwargs={
                'username': self.user.username,
                'post_id': self.post.id}),
            data=form_data,
            follow=True)
        get_comment = Comment.objects.filter(post=self.post,
                                             text='Другой комментарий')
        self.assertFalse(get_comment)

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
