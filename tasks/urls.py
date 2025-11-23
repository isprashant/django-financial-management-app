# apps/tasks/urls.py
from django.urls import path
from . import views

app_name = "tasks"

urlpatterns = [
    path("earn/", views.earn_tasks_view, name="earn"),
    path("task/<int:pk>/", views.task_detail_view, name="task_detail"),
]
