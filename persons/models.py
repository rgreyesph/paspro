from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from core.models import Address, Tag
from accounts.models import ChartOfAccounts
import uuid
from decimal import Decimal

class Employee(models.Model):
    """ Represents an employee of the company. """
    class EmploymentStatus(models.TextChoices): ACTIVE = 'ACTIVE', _('Active'); ON_LEAVE = 'ON_LEAVE', _('On Leave'); TERMINATED = 'TERMINATED', _('Terminated'); CONTRACTOR = 'CONTRACTOR', _('Contractor')
    class PaymentType(models.TextChoices): SALARY = 'SALARY', _('Monthly Salary'); DAILY = 'DAILY', _('Daily Wage'); HOURLY = 'HOURLY', _('Hourly Rate'); PROJECT = 'PROJECT', _('Project Based')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("System User Account"), help_text=_("Link to the Django user account for login, if applicable."), related_name='employee_profile')
    employee_id = models.CharField(_("Employee ID"), max_length=20, unique=True, blank=True, null=True, help_text=_("Unique identifier for the employee."))
    first_name = models.CharField(_("First Name"), max_length=100); last_name = models.CharField(_("Last Name"), max_length=100)
    job_title = models.CharField(_("Job Title"), max_length=150, blank=True)
    email = models.EmailField(_("Email Address"), max_length=254, blank=True, null=True); phone_number = models.CharField(_("Phone Number"), max_length=30, blank=True)
    date_hired = models.DateField(_("Date Hired"), null=True, blank=True); date_terminated = models.DateField(_("Date Terminated"), null=True, blank=True)
    status = models.CharField(_("Employment Status"), max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Primary Address"))
    payment_type = models.CharField(_("Payment Type"), max_length=10, choices=PaymentType.choices, null=True, blank=True)
    monthly_salary = models.DecimalField(_("Monthly Salary"), max_digits=15, decimal_places=2, null=True, blank=True, help_text=_("Enter gross monthly salary if payment type is Salary."))
    daily_wage_rate = models.DecimalField(_("Daily Wage Rate"), max_digits=10, decimal_places=2, null=True, blank=True, help_text=_("Enter daily wage rate if payment type is Daily."))

    # --- Fields for Approval Workflow ---
    manager = models.ForeignKey(
        'self', # Link to another Employee
        on_delete=models.SET_NULL, # Keep employee if manager leaves/deleted
        null=True, blank=True,
        related_name='direct_reports', # How to find employees managed by this person
        verbose_name=_("Direct Manager")
    )
    approval_limit = models.DecimalField(
        _("Approval Limit Amount"), max_digits=15, decimal_places=2,
        null=True, blank=True, default=Decimal('0.00'),
        help_text=_("Maximum amount this employee can approve without needing higher approval.")
    )
    can_ultimately_approve = models.BooleanField(
        _("Can Ultimately Approve?"), default=False,
        help_text=_("Can this employee give final approval regardless of amount (within their workflow level)?")
    )
    # --- End Approval Fields ---

    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = _("Employee"); verbose_name_plural = _("Employees"); ordering = ['last_name', 'first_name']
    def __str__(self): return f"{self.first_name} {self.last_name}"
    @property
    def full_name(self): return f"{self.first_name} {self.last_name}"

class Vendor(models.Model): # ... No changes ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False); name = models.CharField(_("Vendor Name"), max_length=255, help_text=_("Company name or individual's name."))
    contact_person = models.CharField(_("Contact Person"), max_length=150, blank=True, help_text=_("Primary contact at the vendor company."))
    email = models.EmailField(_("Email Address"), max_length=254, blank=True, null=True); phone_number = models.CharField(_("Phone Number"), max_length=30, blank=True)
    website = models.URLField(_("Website"), blank=True); tax_id = models.CharField(_("Tax ID / TIN"), max_length=50, blank=True, help_text=_("Vendor's Tax Identification Number, if applicable."))
    billing_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Billing Address"))
    default_expense_account = models.ForeignKey(ChartOfAccounts, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Default Expense Account"), help_text=_("Default account to use for bills from this vendor."), limit_choices_to={'account_type__in': [ChartOfAccounts.AccountType.EXPENSE]}, related_name='default_vendors')
    is_active = models.BooleanField(_("Is Active"), default=True, help_text=_("Inactive vendors cannot be used in new transactions."))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="vendors"); notes = models.TextField(_("Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = _("Vendor"); verbose_name_plural = _("Vendors"); ordering = ['name']
    def __str__(self): return self.name

class Customer(models.Model): # ... No changes ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False); name = models.CharField(_("Customer Name"), max_length=255, help_text=_("Company name or individual's name."))
    parent_company = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Parent Company"), help_text=_("Link to the parent company, if this is a subsidiary."), related_name='child_customers')
    contact_person = models.CharField(_("Contact Person"), max_length=150, blank=True, help_text=_("Primary contact at the customer company."))
    email = models.EmailField(_("Email Address"), max_length=254, blank=True, null=True); phone_number = models.CharField(_("Phone Number"), max_length=30, blank=True)
    website = models.URLField(_("Website"), blank=True); tax_id = models.CharField(_("Tax ID / TIN"), max_length=50, blank=True, help_text=_("Customer's Tax Identification Number, if applicable."))
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Shipping Address"), related_name='customer_shipping_addresses')
    billing_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Billing Address"), related_name='customer_billing_addresses')
    default_revenue_account = models.ForeignKey(ChartOfAccounts, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Default Revenue Account"), help_text=_("Default account to use for invoices to this customer."), limit_choices_to={'account_type__in': [ChartOfAccounts.AccountType.REVENUE]}, related_name='default_customers')
    is_active = models.BooleanField(_("Is Active"), default=True, help_text=_("Inactive customers cannot be used in new transactions."))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="customers"); notes = models.TextField(_("Notes"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = _("Customer"); verbose_name_plural = _("Customers"); ordering = ['name']
    def __str__(self): return self.name