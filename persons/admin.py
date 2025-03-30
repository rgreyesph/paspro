from django.contrib import admin
from .models import Employee, Vendor, Customer

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'employee_id', 'job_title', 'user', # Added user
        'email', 'phone_number', 'status',
        'payment_type', # Added payment type
        'date_hired'
    )
    list_filter = ('status', 'job_title', 'date_hired', 'payment_type') # Added payment type
    search_fields = (
        'first_name', 'last_name', 'employee_id', 'email', 'job_title',
        'user__username' # Search by linked username
    )
    raw_id_fields = ('address', 'user') # Added user

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone_number', 'default_expense_account', 'is_active')
    list_filter = ('is_active', 'tags')
    search_fields = ('name', 'contact_person', 'email', 'tax_id', 'notes')
    filter_horizontal = ('tags',)
    raw_id_fields = ('billing_address', 'default_expense_account')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'parent_company', 'contact_person', 'email', 'phone_number',
        'default_revenue_account', 'is_active'
    )
    list_filter = ('is_active', 'tags', 'parent_company')
    search_fields = ('name', 'contact_person', 'email', 'tax_id', 'notes', 'parent_company__name')
    filter_horizontal = ('tags',)
    raw_id_fields = (
        'shipping_address', 'billing_address', 'default_revenue_account',
        'parent_company'
    )