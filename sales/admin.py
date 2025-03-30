from django.contrib import admin
from import_export.admin import ImportExportModelAdmin # Import
from .models import SalesInvoice, SalesInvoiceLine

class SalesInvoiceLineInline(admin.TabularInline):
    """ Allows editing lines directly within the Invoice admin view. """
    model = SalesInvoiceLine
    extra = 1 # Number of empty line forms to display
    fields = ('product', 'description', 'quantity', 'unit_price', 'line_total')
    readonly_fields = ('line_total',) # Line total is now auto-calculated and read-only
    autocomplete_fields = ('product',) # Use autocomplete for product selection

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(ImportExportModelAdmin): # Inherit
    list_display = (
        'invoice_number', 'customer', 'project', 'invoice_date', 'due_date',
        'total_amount', 'balance_due', 'status', 'created_by'
    )
    list_filter = ('status', 'customer', 'project', 'invoice_date', 'tags')
    search_fields = ('invoice_number', 'customer__name', 'project__name', 'notes')
    # Add calculated/audit fields to readonly
    readonly_fields = (
        'subtotal', 'tax_amount', 'total_amount', 'balance_due', # amount_paid might be editable or updated via payments
        'created_at', 'updated_at', 'created_by', 'updated_by'
    )
    date_hierarchy = 'invoice_date'
    filter_horizontal = ('tags',)
    inlines = [SalesInvoiceLineInline]
    # Use autocomplete for FKs
    autocomplete_fields = ('customer', 'project', 'created_by', 'updated_by')

    fieldsets = (
         (None, {'fields': ('customer', 'project', 'invoice_number', 'invoice_date', 'due_date', 'status')}),
         ('Amounts', {'fields': ('subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due')}),
         ('Categorization & Notes', {'fields': ('tags', 'notes')}),
         ('Auditing', {'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    def save_model(self, request, obj, form, change):
        """ Auto-populate audit fields """
        if not obj.pk: # If creating new
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    # save_related is needed to trigger recalculation *after* inlines are saved/deleted
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Trigger calculation after lines might have been added/changed/deleted via inline
        # Ensure the instance exists before calculating
        if form.instance:
            form.instance.calculate_totals(save=True)

@admin.register(SalesInvoiceLine)
class SalesInvoiceLineAdmin(ImportExportModelAdmin): # Inherit
    # This admin view is optional, as lines are usually managed via inline
    list_display = ('invoice', 'product', 'description', 'quantity', 'unit_price', 'line_total')
    list_filter = ('invoice__customer', 'product')
    search_fields = ('description', 'invoice__invoice_number', 'product__name')
    autocomplete_fields = ('invoice', 'product') # Use autocomplete
    readonly_fields = ('line_total',) # Auto-calculated