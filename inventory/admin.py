from django.contrib import admin
from .models import Warehouse, Product, StockLevel

# Register your models here.

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_address_summary', 'is_active')
    search_fields = ('name', 'address__street_line_1', 'address__city')
    list_filter = ('is_active',)
    raw_id_fields = ('address',)

    @admin.display(description='Address Summary')
    def get_address_summary(self, obj):
        if obj.address:
            return f"{obj.address.city}, {obj.address.country}"
        return "N/A"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'sku',
        'product_type',
        'track_inventory',
        'sales_price',
        'unit_cost',
        'income_account',
        'expense_cogs_account',
        'is_active'
    )
    list_filter = ('product_type', 'track_inventory', 'is_active', 'tags')
    search_fields = ('name', 'sku', 'description')
    list_editable = ('is_active',)
    filter_horizontal = ('tags',)
    raw_id_fields = ('income_account', 'expense_cogs_account')

@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity_on_hand', 'reorder_point', 'last_stock_update')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku', 'warehouse__name')
    # Use autocomplete_fields for better performance if you have thousands of products/warehouses
    # Needs configuration in the related ModelAdmins (ProductAdmin, WarehouseAdmin)
    # autocomplete_fields = ('product', 'warehouse')
    raw_id_fields = ('product', 'warehouse') # Use raw_id_fields for now
    list_select_related = ('product', 'warehouse') # Optimize query performance