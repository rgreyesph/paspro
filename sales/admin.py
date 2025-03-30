from django.contrib import admin
from .models import SalesInvoice, SalesInvoiceLine

class SalesInvoiceLineInline(admin.TabularInline):
    """ Allows editing lines directly within the Invoice admin view. """
    model = SalesInvoiceLine
    extra = 1 # Number of empty line forms to display
    fields = ('product', 'description', 'quantity', 'unit_price', 'line_total')
    readonly_fields = ('line_total',) # Calculated field
    raw_id_fields = ('product',)
    # autocomplete_fields = ('product',) # Alternative for performance

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'customer', 'project', 'invoice_date', 'due_date',
        'total_amount', 'balance_due', 'status', 'created_by'
    )
    list_filter = ('status', 'customer', 'project', 'invoice_date', 'tags')
    search_fields = ('invoice_number', 'customer__name', 'project__name', 'notes')
    raw_id_fields = ('customer', 'project', 'created_by', 'updated_by') # Include audit fields
    readonly_fields = ('subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due', 'created_at', 'updated_at')
    date_hierarchy = 'invoice_date'
    filter_horizontal = ('tags',)
    inlines = [SalesInvoiceLineInline] # Embed line items

    # TODO: Implement save_model to auto-populate created_by/updated_by
    # def save_model(self, request, obj, form, change):
    #     if not obj.pk: # If creating new
    #         obj.created_by = request.user
    #     obj.updated_by = request.user
    #     super().save_model(request, obj, form, change)

    # TODO: Implement logic to recalculate totals when lines change, possibly via signals

@admin.register(SalesInvoiceLine)
class SalesInvoiceLineAdmin(admin.ModelAdmin):
    """ Optional: Direct admin view for lines if needed, mostly managed via inline. """
    list_display = ('invoice', 'product', 'description', 'quantity', 'unit_price', 'line_total')
    list_filter = ('invoice__customer', 'product') # Example filtering
    search_fields = ('description', 'invoice__invoice_number', 'product__name')
    raw_id_fields = ('invoice', 'product')
    readonly_fields = ('line_total',)