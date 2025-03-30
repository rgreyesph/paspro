from django.contrib import admin
from .models import ChartOfAccounts, DisbursementVoucher # Import models

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(admin.ModelAdmin):
    list_display = (
        'account_number', 'name', 'account_type', 'account_subtype',
        'parent_account', 'is_active', 'updated_at'
    )
    list_filter = ('account_type', 'account_subtype', 'is_active', 'parent_account')
    search_fields = ('account_number', 'name', 'description')
    list_editable = ('is_active',)

# --- Register Disbursement Voucher ---
@admin.register(DisbursementVoucher)
class DisbursementVoucherAdmin(admin.ModelAdmin):
    list_display = (
        'dv_number', 'dv_date', 'payee_name', 'amount', 'status',
        'payment_method', 'check_number', 'bank_account', 'created_by'
    )
    list_filter = ('status', 'dv_date', 'payment_method', 'bank_account')
    search_fields = ('dv_number', 'payee_name', 'notes', 'check_number')
    raw_id_fields = ('bank_account', 'created_by', 'updated_by') # Include audit fields
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'dv_date'

    # TODO: Implement save_model to auto-populate created_by/updated_by