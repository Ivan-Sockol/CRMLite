from django.contrib import admin
from .models import User, Company, Storage, Supplier, Supply, Product, SupplyProduct, Sale, ProductSale

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

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'company')
    search_fields = ('name', 'inn')
    list_filter = ('company',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'purchase_price', 'sale_price', 'company')
    list_filter = ('company',)
    search_fields = ('name',)


class SupplyProductInline(admin.TabularInline):
    model = SupplyProduct
    extra = 1
    raw_id_fields = ('product',)

@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ('id','supplier', 'company', 'delivery_date')
    list_filter = ('company', 'supplier', 'delivery_date')
    readonly_fields = ('delivery_date',)
    inlines = (SupplyProductInline,)

class ProductSaleInline(admin.TabularInline):
    model = ProductSale
    extra = 1
    raw_id_fields = ('product',)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer_name', 'company', 'sale_date')
    list_filter = ('company', 'sale_date')
    readonly_fields = ('sale_date',)
    inlines = (ProductSaleInline,)
    date_hierarchy = 'sale_date'