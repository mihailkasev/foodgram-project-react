from django.contrib import admin

from .models import Subscription, User


class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'first_name',
        'last_name',
        'email'
    )
    list_filter = ('email', 'username')


admin.site.register(User, UserAdmin)
admin.site.register(Subscription)
