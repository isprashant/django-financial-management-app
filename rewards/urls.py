from django.urls import path

from . import views

app_name = "rewards"

urlpatterns = [
    path("rewards/", views.reward_list, name="reward_list"),
    path("rewards/<int:pk>/", views.reward_detail, name="reward_detail"),
]
