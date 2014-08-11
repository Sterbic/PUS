from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from registration.backends.simple.views import RegistrationView

from picshr.views import user_details_view, picture_details_view,\
    UserPictureListView, FriendsPictureListView, PublicPictureListView,\
    UserControlPanelView, submit_comment, like_picture, redirect_home,\
    resolve_friend_request, delete_friend, delete_picture, delete_comment,\
    delete_tag, upload_picture, send_friend_request, add_tag, search_users


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', redirect_home, name='home'),
    url(r'^login/$', 'django.contrib.auth.views.login',
        {'template_name': 'picshr/login.html'}, name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout',
         {'next_page': 'home'}, name='logout'),
    url(r'^accounts/register/$', RegistrationView.as_view(),
        name='register'),
    url(r'^users/(?P<username>\w+)/$', user_details_view, name='user_detail'),
    url(r'^pictures/(?P<picture_id>\d+)/$', picture_details_view,
        name="picture_detail"),
    url(r'^comment/(?P<picture_id>\d+)/(?P<user_id>\d+)/$', submit_comment,
        name='submit_comment'),
    url(r'^like/(?P<picture_id>\d+)/(?P<user_id>\d+)/$', like_picture,
        name='like_picture'),
    url(r'^pictures/my/$', UserPictureListView.as_view(), name='my_pictures'),
    url(r'^pictures/friends/$', FriendsPictureListView.as_view(),
        name='friends_pictures'),
    url(r'^pictures/public/$', PublicPictureListView.as_view(),
        name='public_pictures'),
    url(r'^ctrl/(?P<slug>\w+)/$', UserControlPanelView.as_view(),
        name='control_panel'),
    url(r'^ctrl/friend/resolve/$', resolve_friend_request,
        name='resolve_friend_req'),
    url(r'^ctrl/friend/delete/$', delete_friend, name='delete_friend'),
    url(r'^ctrl/picture/delete/$', delete_picture, name='delete_picture'),
    url(r'^ctrl/comment/delete/$', delete_comment, name='delete_comment'),
    url(r'^ctrl/tag/delete/$', delete_tag, name='delete_tag'),
    url(r'^ctrl/picture/upload/$', upload_picture, name='upload_picture'),
    url(r'^ctrl/friend/request/$', send_friend_request,
        name='send_friend_req'),
    url(r'^ctrl/tag/add/$', add_tag, name='add_tag'),
    url(r'^search/users/$', search_users, name='search_users')
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
