from django.contrib import admin
from .models import TaskType, UserPointsSnapshot, UserTask, Movie, PropertyListing
# Register your models here.

admin.site.register(TaskType)
admin.site.register(UserPointsSnapshot)
admin.site.register(UserTask)
admin.site.register(Movie)
admin.site.register(PropertyListing)


