from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Bill, BillLine

class BillLineInline(admin.TabularInline):
    model = BillLine
    extra = 1
    fields = ('product', 'description', 'account', 'project', 'warehouse', 'quantity', 'unit_price', 'line_total', 'is_vatable', 'bir_classification')
    readonly_fields = ('line_total',)
    autocomplete_fields = ('product', 'account', 'project', 'warehouse')

@admin.register(Bill)
class BillAdmin(ImportExportModelAdmin):
    list_display = ('bill_number', 'vendor', 'bill_date', 'due_date', 'total_amount', 'balance_due', 'status', 'disbursement_voucher', 'get_created_by_username')
    list_filter = ('status', 'vendor', 'bill_date', 'tags', 'disbursement_voucher')
    search_fields = ('bill_number', 'vendor__name', 'notes', 'disbursement_voucher__dv_number')
    readonly_fields = (
        'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due',
        'created_at', 'updated_at', 'created_by', 'updated_by',
        'get_created_by_username', 'get_updated_by_username'
    )
    date_hierarchy = 'bill_date'
    filter_horizontal = ('tags',)
    inlines = [BillLineInline]
    autocomplete_fields = ('vendor', 'disbursement_voucher',)

    fieldsets = (
         (None, {'fields': ('vendor', 'bill_number', 'bill_date', 'due_date', 'status', 'disbursement_voucher')}),
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

@admin.register(BillLine)
class BillLineAdmin(ImportExportModelAdmin):
    list_display = ('bill', 'account', 'project', 'warehouse', 'description', 'quantity', 'unit_price', 'line_total', 'is_vatable')
    list_filter = ('bill__vendor', 'account', 'project', 'warehouse', 'is_vatable')
    search_fields = ('description', 'bill__bill_number', 'product__name', 'account__name', 'project__name', 'warehouse__name')
    autocomplete_fields = ('bill', 'product', 'account', 'project', 'warehouse')
    readonly_fields = ('line_total',)