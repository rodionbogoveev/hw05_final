import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PostsFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='rodion')
        cls.group = Group.objects.create(
            title='Название',
            slug='slug',
            description='Описание',
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        return super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post_with_group(self):
        """Валидная форма создает запись в Post с указанием группы."""
        url = 'index'
        posts_count_before = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('new_post'),
            data=form_data,
            follow=True
        )
        posts_count_after = Post.objects.count()
        get_new_post = Post.objects.get(
            text='Тестовый текст',
            author=self.user,
            group=self.group.id,
            image='posts/small.gif'
        )
        PostsFormTests.post_create_asserts(
            self, response, url, posts_count_after, posts_count_before,
            get_new_post
        )

    def test_create_post_without_group(self):
        """Валидная форма создает запись в Post без указания группы."""
        url = 'index'
        posts_count_before = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='smaller.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст без группы',
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('new_post'),
            data=form_data,
            follow=True
        )
        posts_count_after = Post.objects.count()
        get_new_post = Post.objects.get(
            text='Тестовый текст без группы',
            author=self.user,
            group=None,
            image='posts/smaller.gif'
        )
        PostsFormTests.post_create_asserts(
            self, response, url, posts_count_after, posts_count_before,
            get_new_post
        )

    def test_post_edit(self):
        """При редактировании поста изменяется соответствующая
        запись в базе."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='the_smallest.gif',
            content=small_gif,
            content_type='image/gif'
        )
        new_group = Group.objects.create(
            title='Новое название',
            slug='new_slug',
            description='Новое описание',
        )
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group
        )
        posts_count_before = Post.objects.count()
        form_edit = {
            'text': 'Измененный текст',
            'group': new_group.id,
            'image': uploaded
        }
        self.authorized_client.post(reverse(
            'post_edit',
            kwargs={'username': 'rodion', 'post_id': post.id}),
            data=form_edit,
            follow=True
        )
        posts_count_after = Post.objects.count()
        self.assertFalse(Post.objects.filter(
            text='Тестовый текст',
            group=self.group.id)
        )
        self.assertTrue(Post.objects.filter(
            text='Измененный текст',
            image='posts/the_smallest.gif',
            group=new_group.id)
        )
        self.assertEqual(posts_count_before, posts_count_after)

    def post_create_asserts(self, response, url, posts_count_after,
                            posts_count_before, get_new_post):
        self.assertRedirects(response, reverse(url))
        self.assertEqual(posts_count_after, posts_count_before + 1)
        self.assertTrue(get_new_post)
