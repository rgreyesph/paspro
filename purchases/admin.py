from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Bill, BillLine

class BillLineInline(admin.TabularInline):
    model = BillLine
    extra = 1
    # Add warehouse field
    fields = (
        'product', 'description', 'account', 'project', 'warehouse', 'quantity',
        'unit_price', 'line_total', 'is_vatable', 'bir_classification'
    )
    readonly_fields = ('line_total',)
    # Use autocomplete
    autocomplete_fields = ('product', 'account', 'project', 'warehouse')

@admin.register(Bill)
class BillAdmin(ImportExportModelAdmin):
    list_display = (
        'bill_number', 'vendor', 'bill_date', 'due_date', 'total_amount',
        'balance_due', 'status', 'disbursement_voucher', 'created_by'
    )
    list_filter = ('status', 'vendor', 'bill_date', 'tags', 'disbursement_voucher')
    search_fields = ('bill_number', 'vendor__name', 'notes', 'disbursement_voucher__dv_number')
    # Make amount_paid readonly
    readonly_fields = (
        'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due',
        'created_at', 'updated_at', 'created_by', 'updated_by'
    )
    date_hierarchy = 'bill_date'
    filter_horizontal = ('tags',)
    inlines = [BillLineInline]
    autocomplete_fields = ('vendor', 'disbursement_voucher', 'created_by', 'updated_by')

    fieldsets = (
         (None, {'fields': ('vendor', 'bill_number', 'bill_date', 'due_date', 'status', 'disbursement_voucher')}),
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
        # Signals handle total calculation now
        pass

@admin.register(BillLine)
class BillLineAdmin(ImportExportModelAdmin):
    list_display = ('bill', 'account', 'project', 'warehouse', 'description', 'quantity', 'unit_price', 'line_total', 'is_vatable') # Added warehouse
    list_filter = ('bill__vendor', 'account', 'project', 'warehouse', 'is_vatable') # Added warehouse
    search_fields = ('description', 'bill__bill_number', 'product__name', 'account__name', 'project__name', 'warehouse__name') # Added warehouse
    autocomplete_fields = ('bill', 'product', 'account', 'project', 'warehouse') # Added warehouse
    readonly_fields = ('line_total',)