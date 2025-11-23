from django.contrib import admin

# Register your models here.
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, UserPointsSnapshot, UserProfile
from django.contrib.auth.admin import UserAdmin

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model  = CustomUser
    list_display = ["email", "username", "age", "is_staff"]

admin.site.register(CustomUser, CustomUserAdmin)

admin.site.register(UserPointsSnapshot)
admin.site.register(UserProfile)
