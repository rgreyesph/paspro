from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
# Import EmployeeAdvance from accounts now
from .models import ChartOfAccounts, DisbursementVoucher, EmployeeAdvance

@admin.register(ChartOfAccounts)
class ChartOfAccountsAdmin(ImportExportModelAdmin):
    list_display = ('account_number', 'name', 'account_type', 'account_subtype', 'parent_account', 'is_active', 'updated_at')
    list_filter = ('account_type', 'account_subtype', 'is_active', 'parent_account')
    search_fields = ('account_number', 'name', 'description', 'parent_account__name')
    list_editable = ('is_active',)
    autocomplete_fields = ('parent_account',)

@admin.register(DisbursementVoucher)
class DisbursementVoucherAdmin(ImportExportModelAdmin):
    list_display = ('dv_number', 'dv_date', 'payee_name', 'amount', 'status', 'payment_method', 'check_number', 'bank_account', 'created_by')
    list_filter = ('status', 'dv_date', 'payment_method', 'bank_account')
    search_fields = ('dv_number', 'payee_name', 'notes', 'check_number', 'bank_account__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    date_hierarchy = 'dv_date'
    autocomplete_fields = ('bank_account', 'created_by', 'updated_by')

    fieldsets = (
         (None, {'fields': ('dv_number', 'dv_date', 'payee_name', 'amount', 'status')}),
         ('Payment Details', {'fields': ('payment_method', 'check_number', 'bank_account')}),
         # Added 'notes' here as per model def
         ('Auditing & Notes', {'fields': ('notes', 'created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    # Added missing save_model override
    def save_model(self, request, obj, form, change):
        """ Auto-populate audit fields """
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

# --- EmployeeAdvance Admin Moved Here ---
@admin.register(EmployeeAdvance)
class EmployeeAdvanceAdmin(ImportExportModelAdmin):
    list_display = (
        'employee', 'date_issued', 'amount_issued', 'project', 'status',
        'date_due', 'get_is_overdue_display', # Use display method
        'balance_remaining', 'created_by'
    )
    list_filter = ('status', 'employee', 'project', 'date_issued', 'date_due')
    search_fields = ('employee__first_name', 'employee__last_name', 'purpose', 'project__name', 'asset_account__name') # Search asset account
    list_display_links = ('employee', 'date_issued')
    readonly_fields = ('balance_remaining', 'created_at', 'updated_at', 'created_by', 'updated_by')
    date_hierarchy = 'date_issued'
    # Add asset_account to autocomplete
    autocomplete_fields = ('employee', 'project', 'asset_account', 'created_by', 'updated_by')

    fieldsets = (
        (None, {'fields': ('employee', 'asset_account', 'date_issued', 'amount_issued', 'purpose', 'project', 'date_due', 'status')}), # Added asset_account
        ('Liquidation/Repayment', {'fields': ('amount_liquidated', 'amount_repaid', 'balance_remaining')}),
        ('Auditing', {'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    @admin.display(description='Overdue?', boolean=True)
    def get_is_overdue_display(self, obj):
        return obj.is_overdue

    def save_model(self, request, obj, form, change):
        """ Auto-populate audit fields """
        if not obj.pk:
            obj.created_by = request.user
        # Assign default asset account if not set? Requires fetching the default CoA record.
        # if not obj.asset_account:
        #    try:
        #        default_asset_acc = ChartOfAccounts.objects.get(account_subtype=ChartOfAccounts.AccountSubType.EMPLOYEE_ADVANCES, ...) # Add logic to find default
        #        obj.asset_account = default_asset_acc
        #    except ChartOfAccounts.DoesNotExist: pass # Handle case where default doesn't exist
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)