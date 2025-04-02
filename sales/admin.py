from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import SalesInvoice, SalesInvoiceLine

class SalesInvoiceLineInline(admin.TabularInline):
    """ Allows editing lines directly within the Invoice admin view. """
    model = SalesInvoiceLine
    extra = 1
    # Add warehouse field
    fields = ('product', 'description', 'warehouse', 'quantity', 'unit_price', 'line_total')
    readonly_fields = ('line_total',)
    # Use autocomplete for product and warehouse
    autocomplete_fields = ('product', 'warehouse')

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(ImportExportModelAdmin):
    list_display = ('invoice_number', 'customer', 'project', 'invoice_date', 'due_date', 'total_amount', 'balance_due', 'status', 'created_by')
    list_filter = ('status', 'customer', 'project', 'invoice_date', 'tags')
    search_fields = ('invoice_number', 'customer__name', 'project__name', 'notes')
    # Make amount_paid readonly as it's updated by signals
    readonly_fields = (
        'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due',
        'created_at', 'updated_at', 'created_by', 'updated_by'
    )
    date_hierarchy = 'invoice_date'
    filter_horizontal = ('tags',)
    inlines = [SalesInvoiceLineInline]
    autocomplete_fields = ('customer', 'project', 'created_by', 'updated_by')

    fieldsets = (
         (None, {'fields': ('customer', 'project', 'invoice_number', 'invoice_date', 'due_date', 'status')}),
         ('Amounts', {'fields': ('subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due')}),
         ('Categorization & Notes', {'fields': ('tags', 'notes')}),
         ('Auditing', {'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk: obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Signals handle total calculation now, but may need manual trigger if signals fail
        # Optionally, could force a recalculation here just in case:
        # if form.instance: form.instance.calculate_totals(save=True)
        pass # Let signals handle calculations

@admin.register(SalesInvoiceLine)
class SalesInvoiceLineAdmin(ImportExportModelAdmin):
    list_display = ('invoice', 'product', 'warehouse', 'description', 'quantity', 'unit_price', 'line_total') # Added warehouse
    list_filter = ('invoice__customer', 'product', 'warehouse') # Added warehouse
    search_fields = ('description', 'invoice__invoice_number', 'product__name', 'warehouse__name') # Added warehouse
    autocomplete_fields = ('invoice', 'product', 'warehouse') # Added warehouse
    readonly_fields = ('line_total',)