from django.contrib import admin
from import_export.admin import ImportExportModelAdmin # Import
from .models import ChartOfAccounts, DisbursementVoucher # Import models

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(ImportExportModelAdmin): # Inherit
    list_display = (
        'account_number', 'name', 'account_type', 'account_subtype',
        'parent_account', 'is_active', 'updated_at'
    )
    list_filter = ('account_type', 'account_subtype', 'is_active', 'parent_account')
    search_fields = ('account_number', 'name', 'description', 'parent_account__name')
    list_editable = ('is_active',)
    autocomplete_fields = ('parent_account',) # Use autocomplete for parent

@admin.register(DisbursementVoucher)
class DisbursementVoucherAdmin(ImportExportModelAdmin): # Inherit
    list_display = (
        'dv_number', 'dv_date', 'payee_name', 'amount', 'status',
        'payment_method', 'check_number', 'bank_account', 'created_by'
    )
    list_filter = ('status', 'dv_date', 'payment_method', 'bank_account')
    search_fields = ('dv_number', 'payee_name', 'notes', 'check_number', 'bank_account__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by') # Make audit fields read-only
    date_hierarchy = 'dv_date'
    autocomplete_fields = ('bank_account', 'created_by', 'updated_by') # Use autocomplete

    # Explicitly define fieldsets if you want specific layout or to ensure audit fields show
    fieldsets = (
         (None, {'fields': ('dv_number', 'dv_date', 'payee_name', 'amount', 'status')}),
         ('Payment Details', {'fields': ('payment_method', 'check_number', 'bank_account')}),
         ('Auditing', {'fields': ('notes', 'created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    def save_model(self, request, obj, form, change):
        """ Auto-populate audit fields """
        if not obj.pk: # If creating new
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)