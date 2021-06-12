from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostsModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='rodion')
        cls.group = Group.objects.create(
            title='Название',
            slug='slug',
            description='Описание',
        )
        cls.post = Post.objects.create(
            text='Текст',
            author=cls.user,
            group=cls.group,
        )

    def test_model_name_is_right_field(self):
        """Значение поля __str__ в модели отображается правильно."""
        models = (
            (self.post, self.post.text),
            (self.group, self.group.title)
        )
        for model, value in models:
            with self.subTest(model=model):
                self.assertEqual(value, str(model))
