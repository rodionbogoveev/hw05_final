from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post

User = get_user_model()


@require_GET
def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'posts/index.html', {'page': page})


@require_GET
def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'posts/group.html', {'group': group, 'page': page})


@require_GET
def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    is_following = Follow.objects.filter(
        user=request.user.id,
        author=author)
    follower = author.follower.count()
    following = author.following.count()
    return render(request, 'posts/profile.html',
                  {'author': author, 'page': page,
                   'is_following': is_following, 'user': request.user,
                   'follower': follower, 'following': following})


@require_GET
def post_view(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()
    paginator = Paginator(post_list, 10)
    form = CommentForm(request.POST or None)
    is_following = Follow.objects.filter(
        user=request.user.id,
        author=author)
    follower = author.follower.count()
    following = author.following.count()
    return render(request, 'posts/post.html',
                  {'author': author, 'post': post, 'paginator': paginator,
                   'comments': comments, 'form': form,
                   'is_following': is_following, 'user': request.user,
                   'follower': follower, 'following': following})


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'posts/new_post.html', {'form': form})
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('index')


@login_required
def post_edit(request, username, post_id):
    user = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, id=post_id, author_id=user)
    form = PostForm(request.POST or None, files=request.FILES or None,
                    instance=post)
    if post.author != request.user:
        return redirect('post', username, post_id)
    if form.is_valid():
        form.save()
        return redirect('post', username, post_id)
    return render(request, 'posts/new_post.html', {'form': form, 'post': post})


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('post', username, post_id)


@login_required
def follow_index(request):
    user = get_object_or_404(User, username=request.user.username)
    post_list = Post.objects.filter(author__following__user=user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'posts/follow.html', {'page': page})


@login_required
def profile_follow(request, username):
    user = get_object_or_404(User, username=request.user.username)
    author = get_object_or_404(User, username=username)
    get_follow = Follow.objects.filter(user=user, author=author).exists()
    if user != author and get_follow is False:
        Follow.objects.create(user=user, author=author)
    return redirect('profile', username)


@login_required
def profile_unfollow(request, username):
    user = get_object_or_404(User, username=request.user.username)
    author = get_object_or_404(User, username=username)
    if user != author:
        Follow.objects.filter(user=user, author=author).delete()
    return redirect('profile', username)


def page_not_found(request, exception):
    return render(request, 'misc/404.html', {'path': request.path}, status=404)


def server_error(request):
    return render(request, 'misc/500.html', status=500)
