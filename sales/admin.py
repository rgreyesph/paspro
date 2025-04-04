from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import SalesInvoice, SalesInvoiceLine

class SalesInvoiceLineInline(admin.TabularInline):
    model = SalesInvoiceLine
    extra = 1
    fields = ('product', 'description', 'warehouse', 'quantity', 'unit_price', 'is_vat_exempt', 'line_total')
    readonly_fields = ('line_total',)
    autocomplete_fields = ('product', 'warehouse')

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(ImportExportModelAdmin):
    list_display = ('invoice_number', 'customer', 'project', 'invoice_date', 'due_date', 'total_amount', 'balance_due', 'status', 'get_created_by_username')
    list_filter = ('status', 'customer', 'project', 'invoice_date', 'tags')
    search_fields = ('invoice_number', 'customer__name', 'project__name', 'notes')
    readonly_fields = (
        'subtotal', 'tax_amount', 'total_amount', 'amount_paid',
        'balance_due', 'created_at', 'updated_at', 'created_by', 'updated_by',
        'get_created_by_username', 'get_updated_by_username'
    )
    date_hierarchy = 'invoice_date'
    filter_horizontal = ('tags',)
    inlines = [SalesInvoiceLineInline]
    autocomplete_fields = ('customer', 'project',)

    fieldsets = (
         (None, {'fields': ('customer', 'project', 'invoice_number', 'invoice_date', 'due_date', 'status')}),
         ('Amounts', {'fields': ('subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due')}),
         ('Categorization & Notes', {'fields': ('tags', 'notes')}),
         ('Auditing', {'fields': ('created_at', 'get_created_by_username', 'updated_at', 'get_updated_by_username')}),
    )

    @admin.display(description='Created By')
    def get_created_by_username(self, obj): return obj.created_by.username if obj.created_by else None
    @admin.display(description='Updated By')
    def get_updated_by_username(self, obj): return obj.updated_by.username if obj.updated_by else None

    # --- Revised save_model logic ---
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            obj.created_by = request.user
            obj.save(update_fields=['created_by'])
    # --- End revised logic ---

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if form.instance: form.instance.calculate_totals(save=True)

@admin.register(SalesInvoiceLine)
class SalesInvoiceLineAdmin(ImportExportModelAdmin):
    list_display = ('invoice', 'product', 'warehouse', 'description', 'quantity', 'unit_price', 'is_vat_exempt', 'line_total')
    list_filter = ('invoice__customer', 'product', 'warehouse', 'is_vat_exempt')
    search_fields = ('description', 'invoice__invoice_number', 'product__name', 'warehouse__name')
    autocomplete_fields = ('invoice', 'product', 'warehouse')
    readonly_fields = ('line_total',)