from django.contrib import admin
from .models import Bill, BillLine

class BillLineInline(admin.TabularInline):
    model = BillLine
    extra = 1
    fields = (
        'product', 'description', 'account', 'project', 'quantity',
        'unit_price', 'line_total', 'is_vatable', 'bir_classification'
    )
    readonly_fields = ('line_total',)
    raw_id_fields = ('product', 'account', 'project')
    # autocomplete_fields = ('product', 'account', 'project') # Alternative

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = (
        'bill_number', 'vendor', 'bill_date', 'due_date', 'total_amount',
        'balance_due', 'status', 'disbursement_voucher', 'created_by'
    )
    list_filter = ('status', 'vendor', 'bill_date', 'tags', 'disbursement_voucher')
    search_fields = ('bill_number', 'vendor__name', 'notes', 'disbursement_voucher__dv_number')
    raw_id_fields = ('vendor', 'disbursement_voucher', 'created_by', 'updated_by')
    readonly_fields = ('subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due', 'created_at', 'updated_at')
    date_hierarchy = 'bill_date'
    filter_horizontal = ('tags',)
    inlines = [BillLineInline]

    # TODO: Implement save_model to auto-populate created_by/updated_by
    # TODO: Implement logic to recalculate totals

@admin.register(BillLine)
class BillLineAdmin(admin.ModelAdmin):
    list_display = ('bill', 'account', 'project', 'description', 'quantity', 'unit_price', 'line_total', 'is_vatable')
    list_filter = ('bill__vendor', 'account', 'project', 'is_vatable')
    search_fields = ('description', 'bill__bill_number', 'product__name', 'account__name', 'project__name')
    raw_id_fields = ('bill', 'product', 'account', 'project')
    readonly_fields = ('line_total',)