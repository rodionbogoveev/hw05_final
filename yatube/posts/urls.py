from django.urls import path

from . import views

urlpatterns = [
    # Главная страница
    path('', views.index, name='index'),
    # Добавление новой публикации
    path('new/', views.new_post, name='new_post'),
    # Страница группы
    path('group/<slug>/', views.group_posts, name='group_posts'),
    # Профайл пользователя
    path('<str:username>/', views.profile, name='profile'),
    # Просмотр записи
    path('<str:username>/<int:post_id>/', views.post_view, name='post'),
    # Добавление комментария
    path('<username>/<int:post_id>/comment', views.add_comment,
         name='add_comment'),
    # Редактирование записи
    path('<str:username>/<int:post_id>/edit/', views.post_edit,
         name='post_edit'),
]
