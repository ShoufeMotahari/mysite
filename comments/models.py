# from django.db import models
# from django.conf import settings
#
# class Comment(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     content = models.TextField()
#     created = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return f"{self.user} - {self.content[:30]}"