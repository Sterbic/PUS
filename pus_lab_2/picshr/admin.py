from django.contrib import admin

from picshr.models import Picture, Friend, FriendRequest, Comment

admin.site.register(FriendRequest)
admin.site.register(Friend)
admin.site.register(Picture)
admin.site.register(Comment)