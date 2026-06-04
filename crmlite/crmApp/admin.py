from django.contrib import admin
from .models import User, Company, Storage

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_company_owner', 'company')
    search_fields = ('email',)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('inn', 'title', 'owner')
    search_fields = ('inn', 'title')

@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ('address', 'company')
    list_filter = ('company', )
