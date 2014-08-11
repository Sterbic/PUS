from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView, DetailView
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from picshr.models import Picture, Comment, Friend, FriendRequest


def user_details_view(request, username):
    other_user = get_object_or_404(User, username=username)
    public_pics = other_user.picture_set.filter(is_public=True)
    private_pics = None

    private_access = False

    if request.user.username == username:
        private_access = True
    else:
        for friend in request.user.is_friend_set.all():
            if username == friend.friend_to.username:
                private_access = True
                break

    if private_access:
        private_pics = other_user.picture_set.filter(is_public=False)

    return render(request, "picshr/user_detail.html",
                  {"public_pics": public_pics, "private_pics": private_pics,
                   "private_access": private_access, "other_user": other_user})


class UserControlPanelView(DetailView):
    model = User
    slug_field = "username"
    template_name = "picshr/control_panel.html"


def picture_details_view(request, picture_id):
    picture = Picture.objects.get(pk=picture_id)
    liked_picture = request.user in picture.likes.all()

    friends_sel = [request.user.username]
    for friend in request.user.is_friend_set.all():
        friends_sel.append(friend.friend_to)

    return render(request, "picshr/picture_detail.html",
                  {"picture": picture, "liked_picture": liked_picture,
                   "friends_sel": friends_sel})

class UserPictureListView(ListView):
    model = Picture
    template_name = 'picshr/picture_list.html'

    def get_queryset(self):
        return Picture.objects.filter(author=self.request.user)


class FriendsPictureListView(ListView):
    model = Picture
    template_name = 'picshr/picture_list.html'

    def get_queryset(self):
        friends = [friend.friend_to for friend
                   in self.request.user.is_friend_set.all()]
        return Picture.objects.filter(author__in=friends)


class PublicPictureListView(ListView):
    model = Picture
    template_name = 'picshr/picture_list.html'

    def get_queryset(self):
        return Picture.objects.filter(is_public=True)


def submit_comment(request, picture_id, user_id):
    user = get_object_or_404(User, pk=user_id)
    picture = get_object_or_404(Picture, pk=picture_id)

    try:
        content = request.POST["content"]
        comment = Comment(content=content, author=user, on_picture=picture)

        if content:
            comment.save()
    except KeyError:
        pass

    return HttpResponseRedirect(reverse('picture_detail', args=(picture_id,)))

def like_picture(request, picture_id, user_id):
    user = get_object_or_404(User, pk=user_id)
    picture = get_object_or_404(Picture, pk=picture_id)

    if user in picture.likes.all():
        picture.likes.remove(user)
    else:
        picture.likes.add(user)

    picture.save()

    return HttpResponseRedirect(reverse('picture_detail', args=(picture_id,)))


def redirect_home(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_detail',
                                    args=(request.user.username,)))
    else:
        return HttpResponseRedirect(reverse('login'))


def resolve_friend_request(request):
    user = request.user

    try:
        friend_req = FriendRequest.objects.get(pk=request.POST['req_id'])

        if request.POST['response'] == 'accept':
            first = Friend(is_friend=user, friend_to=friend_req.req_from)
            second = Friend(is_friend=friend_req.req_from, friend_to=user)

            first.save()
            second.save()

        friend_req.delete()
    except (KeyError, FriendRequest.DoesNotExist):
        pass

    return HttpResponseRedirect(reverse('control_panel',
                                        args=(user.username,)))


def delete_friend(request):
    user = request.user

    try:
        friend = Friend.objects.get(pk=request.POST['friend_id'])
        friend_other = Friend.objects.get(
            is_friend=friend.friend_to,
            friend_to=user
        )

        friend.delete()
        friend_other.delete()
    except (KeyError, Friend.DoesNotExist):
        pass

    return HttpResponseRedirect(reverse('control_panel',
                                        args=(user.username,)))


def delete_picture(request):
    try:
        picture = Picture.objects.get(pk=request.POST['picture_id'])
        picture.delete()
    except (KeyError, Picture.DoesNotExist):
        pass

    return HttpResponseRedirect(reverse('control_panel',
                                        args=(request.user.username,)))


def delete_comment(request):
    try:
        comment = Comment.objects.get(pk=request.POST['comment_id'])
        comment.delete()
    except (KeyError, Comment.DoesNotExist):
        pass

    return HttpResponseRedirect(reverse('control_panel',
                                        args=(request.user.username,)))


def delete_tag(request):
    try:
        picture = Picture.objects.get(pk=request.POST['picture_id'])
        picture.tags.remove(request.user)
        picture.save()
    except (KeyError, Picture.DoesNotExist):
        pass

    return HttpResponseRedirect(reverse('control_panel',
                                        args=(request.user.username,)))


def upload_picture(request):
    if request.method == 'POST':
        picture = Picture()

        picture.title = request.POST['title']
        picture.is_public = request.POST['visibility'] == 'public'
        picture.author = request.user
        picture.image = request.FILES['file']

        picture.save()
        return HttpResponseRedirect(reverse('home'))
    else:
        return render(request, 'picshr/picture_upload.html')


def send_friend_request(request):
    try:
        other = User.objects.get(pk=request.POST['user_id'])
        friend_req = FriendRequest(req_from=request.user, req_to=other)
        friend_req.save()
    except (KeyError, User.DoesNotExist):
        pass

    return HttpResponseRedirect(reverse('user_detail', args=(other.username,)))


def add_tag(request):
    try:
        picture = Picture.objects.get(pk=request.POST['picture_id'])
        user = User.objects.get(username=request.POST['tag_username'])

        picture.tags.add(user)
        picture.save()
    except (KeyError, Picture.DoesNotExist, User.DoesNotExist):
        pass

    return HttpResponseRedirect(reverse('picture_detail', args=(picture.pk,)))


def search_users(request):
    matched = []

    try:
        query = request.POST['query']

        for user in User.objects.all():
            if query in user.username:
                matched.append(user.username)
    except KeyError:
        pass

    return render(request, 'picshr/search_results.html', {'matched': matched})