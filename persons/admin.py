from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
# EmployeeAdvance model/admin is removed from here
from .models import Employee, Vendor, Customer

@admin.register(Employee)
class EmployeeAdmin(ImportExportModelAdmin):
    list_display = ('full_name', 'employee_id', 'job_title', 'user', 'email', 'phone_number', 'status', 'payment_type', 'date_hired')
    list_filter = ('status', 'job_title', 'date_hired', 'payment_type')
    search_fields = ('first_name', 'last_name', 'employee_id', 'email', 'job_title', 'user__username')
    raw_id_fields = ('user',)
    autocomplete_fields = ('address',)

@admin.register(Vendor)
class VendorAdmin(ImportExportModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone_number', 'default_expense_account', 'is_active')
    list_filter = ('is_active', 'tags')
    search_fields = ('name', 'contact_person', 'email', 'tax_id', 'notes', 'default_expense_account__name')
    filter_horizontal = ('tags',)
    autocomplete_fields = ('billing_address', 'default_expense_account')

@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    list_display = ('name', 'parent_company', 'contact_person', 'email', 'phone_number', 'default_revenue_account', 'is_active')
    list_filter = ('is_active', 'tags', 'parent_company')
    search_fields = ('name', 'contact_person', 'email', 'tax_id', 'notes', 'parent_company__name', 'default_revenue_account__name')
    filter_horizontal = ('tags',)
    autocomplete_fields = ('shipping_address', 'billing_address', 'default_revenue_account', 'parent_company')

# EmployeeAdvanceAdmin registration is removed from this file