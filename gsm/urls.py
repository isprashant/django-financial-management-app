from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("ui_gsm.urls")),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('', include('users.urls')),
    path('', include('django.contrib.auth.urls')),
    path("", include("referrals.urls", namespace="referrals")),
    path("", include("rewards.urls", namespace="rewards")),
    path("tasks/", include("tasks.urls", namespace="tasks")),
    path("payments/", include("payments.urls", namespace="payments")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
