from django.urls import path
from . import views
from tasks.views import earn_tasks_view
from investments.views import funds_overview, scheme_detail

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("funds/", funds_overview, name="funds"),
    path("investments/<int:pk>/", scheme_detail, name="investment_detail"),
    path("earn/", earn_tasks_view, name="earn"),
    path("join/", views.join, name="join"),
    path("invite/", views.invite, name="invite"),
    path("growth/", views.growth, name="growth"),
]
