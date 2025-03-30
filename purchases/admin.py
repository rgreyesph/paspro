from django.contrib import admin
from import_export.admin import ImportExportModelAdmin # Import
from .models import Bill, BillLine

class BillLineInline(admin.TabularInline):
    model = BillLine
    extra = 1
    fields = (
        'product', 'description', 'account', 'project', 'quantity',
        'unit_price', 'line_total', 'is_vatable', 'bir_classification'
    )
    readonly_fields = ('line_total',) # Auto-calculated and read-only
    autocomplete_fields = ('product', 'account', 'project') # Use autocomplete

@admin.register(Bill)
class BillAdmin(ImportExportModelAdmin): # Inherit
    list_display = (
        'bill_number', 'vendor', 'bill_date', 'due_date', 'total_amount',
        'balance_due', 'status', 'disbursement_voucher', 'created_by'
    )
    list_filter = ('status', 'vendor', 'bill_date', 'tags', 'disbursement_voucher')
    search_fields = ('bill_number', 'vendor__name', 'notes', 'disbursement_voucher__dv_number')
    # Make totals and audit fields read-only
    readonly_fields = (
        'subtotal', 'tax_amount', 'total_amount', 'balance_due', # amount_paid might be editable or updated via payments
        'created_at', 'updated_at', 'created_by', 'updated_by'
    )
    date_hierarchy = 'bill_date'
    filter_horizontal = ('tags',)
    inlines = [BillLineInline]
    # Use autocomplete for FKs
    autocomplete_fields = ('vendor', 'disbursement_voucher', 'created_by', 'updated_by')

    fieldsets = (
         (None, {'fields': ('vendor', 'bill_number', 'bill_date', 'due_date', 'status', 'disbursement_voucher')}),
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

    # save_related to trigger calculation after lines are saved/deleted
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Ensure the instance exists before calculating
        if form.instance:
            form.instance.calculate_totals(save=True)

@admin.register(BillLine)
class BillLineAdmin(ImportExportModelAdmin): # Inherit
    # Optional direct admin view for lines
    list_display = ('bill', 'account', 'project', 'description', 'quantity', 'unit_price', 'line_total', 'is_vatable')
    list_filter = ('bill__vendor', 'account', 'project', 'is_vatable')
    search_fields = ('description', 'bill__bill_number', 'product__name', 'account__name', 'project__name')
    autocomplete_fields = ('bill', 'product', 'account', 'project') # Use autocomplete
    readonly_fields = ('line_total',) # Auto-calculated