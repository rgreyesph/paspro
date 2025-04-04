from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from core.models import Address, Tag # Import core models
from accounts.models import ChartOfAccounts # Import accounts for Product FK widget
from .models import Warehouse, Product, StockLevel # Import inventory models

class WarehouseResource(resources.ModelResource):
    address_display = fields.Field(
        column_name='Address',
        attribute='address',
        widget=ForeignKeyWidget(Address, field='full_address')
    )

    class Meta:
        model = Warehouse
        # Define fields to include, explicitly excluding 'id'
        fields = ('name', 'address_display', 'is_active', 'created_at', 'updated_at')
        export_order = ('name', 'address_display', 'is_active', 'created_at', 'updated_at')
        # Alternatively, use exclude: exclude = ('id', 'address',)

class ProductResource(resources.ModelResource):
    income_account_display = fields.Field(
        column_name='Income Account',
        attribute='income_account',
        widget=ForeignKeyWidget(ChartOfAccounts, field='name')
    )
    expense_cogs_account_display = fields.Field(
        column_name='Expense/COGS Account',
        attribute='expense_cogs_account',
        widget=ForeignKeyWidget(ChartOfAccounts, field='name')
    )
    # Example for Tags if needed:
    # tags_display = fields.Field(attribute='tags', widget=ManyToManyWidget(Tag, field='name', separator=' | '))

    class Meta:
        model = Product
        # Define fields to export, excluding 'id' and raw FKs for accounts
        fields = (
            'name', 'sku', 'description', 'product_type', 'track_inventory',
            'unit_cost', 'sales_price',
            'income_account_display',
            'expense_cogs_account_display',
            'is_active', 'created_at', 'updated_at', # 'tags_display'
        )
        export_order = fields
        # Alternatively use exclude:
        # exclude = ('id', 'income_account', 'expense_cogs_account', 'tags')

# You can add resources for other models like StockLevel here following the same pattern