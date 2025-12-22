from django.urls import path

from .views import SignUpView, profile_view, profile_edit

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("profile/", profile_view, name="profile"),
    path("profile/edit/", profile_edit, name="profile_edit"),
]
