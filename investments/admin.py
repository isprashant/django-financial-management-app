from django.contrib import admin
from .models import InvestmentReturnLog, InvestmentScheme, UserInvestment
# Register your models here.

admin.site.register(InvestmentReturnLog)
admin.site.register(InvestmentScheme)
admin.site.register(UserInvestment)

