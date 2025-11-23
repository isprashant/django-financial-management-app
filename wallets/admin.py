from django.contrib import admin
from .models import Wallet, WithdrawalRequest, WalletTransaction, Deposit
# Register your models here.

admin.site.register(WalletTransaction)
admin.site.register(Wallet)
admin.site.register(WithdrawalRequest)
admin.site.register(Deposit)
