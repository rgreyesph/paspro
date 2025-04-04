from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
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
    list_display = ('dv_number', 'dv_date', 'payee_name', 'amount', 'status', 'payment_method', 'check_number', 'bank_account', 'get_created_by_username')
    list_filter = ('status', 'dv_date', 'payment_method', 'bank_account')
    search_fields = ('dv_number', 'payee_name', 'notes', 'check_number', 'bank_account__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by', 'get_created_by_username', 'get_updated_by_username')
    date_hierarchy = 'dv_date'
    autocomplete_fields = ('bank_account',)

    fieldsets = (
         (None, {'fields': ('dv_number', 'dv_date', 'payee_name', 'amount', 'status')}),
         ('Payment Details', {'fields': ('payment_method', 'check_number', 'bank_account')}),
         ('Auditing & Notes', {'fields': ('notes', 'created_at', 'get_created_by_username', 'updated_at', 'get_updated_by_username')}),
    )

    @admin.display(description='Created By')
    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else None

    @admin.display(description='Updated By')
    def get_updated_by_username(self, obj):
        return obj.updated_by.username if obj.updated_by else None

    # --- Revised save_model logic ---
    def save_model(self, request, obj, form, change):
        """ Auto-populate audit fields using save-first approach. """
        # Always set updated_by before any save
        obj.updated_by = request.user

        # Save the object initially (or for changes)
        # This populates obj.pk if it's a new instance
        super().save_model(request, obj, form, change)

        # If it was a new object creation ('change' is False)
        if not change:
            # Set created_by *after* the initial save generated the PK
            obj.created_by = request.user
            # Save again, only updating the created_by field
            obj.save(update_fields=['created_by'])
    # --- End revised logic ---


@admin.register(EmployeeAdvance)
class EmployeeAdvanceAdmin(ImportExportModelAdmin):
    list_display = ('advance_number', 'employee', 'date_issued', 'amount_issued', 'project', 'status', 'date_due', 'get_is_overdue_display', 'balance_remaining', 'get_created_by_username')
    list_filter = ('status', 'employee', 'project', 'date_issued', 'date_due')
    search_fields = ('advance_number', 'employee__first_name', 'employee__last_name', 'purpose', 'project__name', 'asset_account__name')
    list_display_links = ('advance_number', 'employee')
    readonly_fields = ('balance_remaining', 'created_at', 'updated_at', 'created_by', 'updated_by', 'get_created_by_username', 'get_updated_by_username')
    date_hierarchy = 'date_issued'
    autocomplete_fields = ('employee', 'project', 'asset_account',)

    def get_fieldsets(self, request, obj=None):
        base_fieldsets = [
            (None, {'fields': ('advance_number', 'employee', 'asset_account', 'date_issued', 'amount_issued', 'purpose', 'project', 'date_due', 'status')}),
            ('Liquidation/Repayment', {'fields': ('amount_liquidated', 'amount_repaid', 'balance_remaining')}),
        ]
        audit_fields = ['created_at', 'get_created_by_username', 'updated_at', 'get_updated_by_username']
        base_fieldsets.append(('Auditing', {'fields': audit_fields}))
        return base_fieldsets

    @admin.display(description='Overdue?', boolean=True)
    def get_is_overdue_display(self, obj): return obj.is_overdue
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