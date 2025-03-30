from django.contrib import admin
from import_export.admin import ImportExportModelAdmin # Import
from .models import Employee, Vendor, Customer, EmployeeAdvance # Add EmployeeAdvance

@admin.register(Employee)
class EmployeeAdmin(ImportExportModelAdmin): # Inherit
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
    raw_id_fields = ('user',) # Keep user as raw_id for default Django UI
    autocomplete_fields = ('address',) # Change address to autocomplete
    # resource_class = EmployeeResource # Optional: Define for custom import/export fields/logic

@admin.register(Vendor)
class VendorAdmin(ImportExportModelAdmin): # Inherit
    list_display = ('name', 'contact_person', 'email', 'phone_number', 'default_expense_account', 'is_active')
    list_filter = ('is_active', 'tags')
    search_fields = ('name', 'contact_person', 'email', 'tax_id', 'notes', 'default_expense_account__name') # Search account name
    filter_horizontal = ('tags',)
    # Change FKs to autocomplete
    autocomplete_fields = ('billing_address', 'default_expense_account')

@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin): # Inherit
    list_display = (
        'name', 'parent_company', 'contact_person', 'email', 'phone_number',
        'default_revenue_account', 'is_active'
    )
    list_filter = ('is_active', 'tags', 'parent_company')
    search_fields = ('name', 'contact_person', 'email', 'tax_id', 'notes', 'parent_company__name', 'default_revenue_account__name')
    filter_horizontal = ('tags',)
    # Change FKs to autocomplete
    autocomplete_fields = ('shipping_address', 'billing_address', 'default_revenue_account', 'parent_company')

# --- New Employee Advance Admin ---
@admin.register(EmployeeAdvance)
class EmployeeAdvanceAdmin(ImportExportModelAdmin): # Inherit
    list_display = (
        'employee', 'date_issued', 'amount_issued', 'project', 'status',
        'date_due', 'get_is_overdue_display', # Use display method
        'balance_remaining', 'created_by'
    )
    list_filter = ('status', 'employee', 'project', 'date_issued', 'date_due')
    search_fields = ('employee__first_name', 'employee__last_name', 'purpose', 'project__name')
    list_display_links = ('employee', 'date_issued') # Make these clickable links to detail view
    readonly_fields = (
        'balance_remaining', 'created_at', 'updated_at', 'created_by', 'updated_by'
    ) # is_overdue is dynamic, not stored
    date_hierarchy = 'date_issued'
    autocomplete_fields = ('employee', 'project', 'created_by', 'updated_by') # Use autocomplete

    # Need to explicitly add 'created_by', 'updated_by' to fieldsets if not default
    fieldsets = (
        (None, {'fields': ('employee', 'date_issued', 'amount_issued', 'purpose', 'project', 'date_due', 'status')}),
        ('Liquidation/Repayment', {'fields': ('amount_liquidated', 'amount_repaid', 'balance_remaining')}),
        ('Auditing', {'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    @admin.display(description='Overdue?', boolean=True)
    def get_is_overdue_display(self, obj): # Method to display the property as a boolean icon
        return obj.is_overdue

    def save_model(self, request, obj, form, change):
        """ Auto-populate audit fields """
        if not obj.pk: # If creating new
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)