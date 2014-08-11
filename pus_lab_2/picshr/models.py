from django.db import models
from django.contrib.auth.models import User


def upload_where(instance, filename):
    return '%s/%s' % (instance.author.username, filename)


class FriendRequest(models.Model):
    req_from = models.ForeignKey(User, related_name="req_from_set")
    req_to = models.ForeignKey(User, related_name="req_to_set")

    def __str__(self):
        return "%s sent a request to %s" % (self.req_from.username,
                                            self.req_to.username)


class Friend(models.Model):
    is_friend = models.ForeignKey(User, related_name="is_friend_set")
    friend_to = models.ForeignKey(User, related_name="friend_to_set")

    def __str__(self):
        return "%s is friend to %s" % (self.is_friend.username,
                                       self.friend_to.username)


class Picture(models.Model):
    title = models.CharField(max_length=30)
    image = models.ImageField(upload_to=upload_where)
    author = models.ForeignKey(User)
    is_public = models.BooleanField()
    likes = models.ManyToManyField(User, related_name="likes", blank=True)
    tags = models.ManyToManyField(User, related_name="tags", blank=True)
    submitted_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s (%s)" % (self.title, self.author.username)


class Comment(models.Model):
    author = models.ForeignKey(User)
    on_picture = models.ForeignKey(Picture)
    submitted_on = models.DateTimeField(auto_now_add=True)
    content = models.TextField(max_length=140)

    def __str__(self):
        return "%s (%s)" % (self.content, self.author.username)