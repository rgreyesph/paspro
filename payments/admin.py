from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import PaymentReceived, PaymentMade

@admin.register(PaymentReceived)
class PaymentReceivedAdmin(ImportExportModelAdmin):
    list_display = (
        'payment_date', 'customer', 'amount', 'payment_method',
        'reference_number', 'account_deposited_to', 'created_by'
    )
    list_filter = ('payment_date', 'customer', 'payment_method', 'account_deposited_to', 'tags')
    search_fields = ('customer__name', 'reference_number', 'notes', 'invoices__invoice_number')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    date_hierarchy = 'payment_date'
    autocomplete_fields = ('customer', 'account_deposited_to', 'invoices', 'created_by', 'updated_by')
    # Use filter_horizontal for ManyToMany 'invoices' and 'tags'
    filter_horizontal = ('invoices', 'tags')

    fieldsets = (
         (None, {'fields': ('customer', 'payment_date', 'amount', 'account_deposited_to')}),
         ('Details', {'fields': ('payment_method', 'reference_number')}),
         ('Related Documents', {'fields': ('invoices',)}),
         ('Auditing & Categorization', {'fields': ('notes', 'tags', 'created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk: obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        # TODO: Add logic here or via signal to update related Invoice amount_paid

@admin.register(PaymentMade)
class PaymentMadeAdmin(ImportExportModelAdmin):
    list_display = (
        'payment_date', 'get_payee_display', 'amount', 'payment_method',
        'reference_number', 'account_paid_from', 'disbursement_voucher', 'created_by'
    )
    list_filter = ('payment_date', 'payee_type', 'vendor', 'employee', 'payment_method', 'account_paid_from', 'tags')
    search_fields = (
        'vendor__name', 'employee__first_name', 'employee__last_name', 'other_payee_name',
        'reference_number', 'notes', 'bills__bill_number', 'disbursement_voucher__dv_number',
        'employee_advance_issued__employee__first_name' # Search related advance employee
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    date_hierarchy = 'payment_date'
    autocomplete_fields = (
        'vendor', 'employee', 'account_paid_from', 'disbursement_voucher',
        'employee_advance_issued', 'bills', 'created_by', 'updated_by'
    )
    # Use filter_horizontal for ManyToMany 'bills' and 'tags'
    filter_horizontal = ('bills', 'tags')

    fieldsets = (
        (None, {'fields': ('payment_date', 'amount', 'account_paid_from')}),
        ('Payee', {'fields': ('payee_type', 'vendor', 'employee', 'other_payee_name')}),
        ('Payment Details', {'fields': ('payment_method', 'reference_number')}),
        ('Related Documents', {'fields': ('bills', 'disbursement_voucher', 'employee_advance_issued')}),
        ('Auditing & Categorization', {'fields': ('notes', 'tags', 'created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    @admin.display(description='Payee')
    def get_payee_display(self, obj):
        return obj.get_payee_name()

    def save_model(self, request, obj, form, change):
        if not obj.pk: obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        # TODO: Add logic here or via signal to update related Bill amount_paid or Advance status