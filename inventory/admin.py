from django.contrib import admin
from import_export.admin import ImportExportModelAdmin # Import
from .models import Warehouse, Product, StockLevel

@admin.register(Warehouse)
class WarehouseAdmin(ImportExportModelAdmin): # Inherit
    list_display = ('name', 'get_address_summary', 'is_active')
    search_fields = ('name', 'address__street_line_1', 'address__city')
    list_filter = ('is_active',)
    autocomplete_fields = ('address',) # Change to autocomplete

    @admin.display(description='Address Summary')
    def get_address_summary(self, obj):
        if obj.address: return f"{obj.address.city}, {obj.address.country}"
        return "N/A"

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin): # Inherit
    list_display = (
        'name', 'sku', 'product_type', 'track_inventory', 'sales_price',
        'unit_cost', 'income_account', 'expense_cogs_account', 'is_active'
    )
    list_filter = ('product_type', 'track_inventory', 'is_active', 'tags')
    # Add account names to search fields
    search_fields = ('name', 'sku', 'description', 'income_account__name', 'expense_cogs_account__name')
    list_editable = ('is_active',)
    filter_horizontal = ('tags',)
    autocomplete_fields = ('income_account', 'expense_cogs_account') # Change to autocomplete

@admin.register(StockLevel)
class StockLevelAdmin(ImportExportModelAdmin): # Inherit
    list_display = ('product', 'warehouse', 'quantity_on_hand', 'reorder_point', 'last_stock_update')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku', 'warehouse__name')
    autocomplete_fields = ('product', 'warehouse') # Change to autocomplete
    list_select_related = ('product', 'warehouse') # Optimize query performance