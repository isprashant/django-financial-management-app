from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("start/<int:order_id>/", views.start_payment, name="start"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/status/", views.order_status, name="order_status"),
    path("easebuzz/callback/", views.easebuzz_callback, name="callback"),
]
