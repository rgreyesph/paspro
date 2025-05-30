from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from core.models import AuditableModel
import uuid
from decimal import Decimal

def get_default_advance_due_date():
    return timezone.now().date() + timedelta(days=7)

class ChartOfAccounts(models.Model):
    class AccountType(models.TextChoices): ASSET = 'ASSET', _('Asset'); LIABILITY = 'LIABILITY', _('Liability'); EQUITY = 'EQUITY', _('Equity'); REVENUE = 'REVENUE', _('Revenue'); EXPENSE = 'EXPENSE', _('Expense')
    class AccountSubType(models.TextChoices):
        BANK = 'BANK', _('Bank'); CASH = 'CASH', _('Cash / Petty Cash')
        ACCOUNTS_RECEIVABLE = 'ACCOUNTS_RECEIVABLE', _('Accounts Receivable (A/R)')
        EMPLOYEE_ADVANCES = 'EMPLOYEE_ADVANCES', _('Employee Advances (Asset)')
        INVENTORY = 'INVENTORY', _('Inventory'); PREPAID_EXPENSES = 'PREPAID_EXPENSES', _('Prepaid Expenses')
        OTHER_CURRENT_ASSET = 'OTHER_CURRENT_ASSET', _('Other Current Asset')
        FIXED_ASSET = 'FIXED_ASSET', _('Fixed Asset')
        ACCOUNTS_PAYABLE = 'ACCOUNTS_PAYABLE', _('Accounts Payable (A/P)')
        CREDIT_CARD_PAYABLE = 'CREDIT_CARD_PAYABLE', _('Credit Card Payable')
        ACCRUED_LIABILITIES = 'ACCRUED_LIABILITIES', _('Accrued Liabilities')
        UNEARNED_REVENUE = 'UNEARNED_REVENUE', _('Unearned Revenue')
        CURRENT_LIABILITY = 'CURRENT_LIABILITY', _('Other Current Liability')
        LONG_TERM_LIABILITY = 'LONG_TERM_LIABILITY', _('Long-Term Liability')
        OWNERS_EQUITY = 'OWNERS_EQUITY', _("Owner's Equity"); RETAINED_EARNINGS = 'RETAINED_EARNINGS', _('Retained Earnings')
        SALES = 'SALES', _('Sales Revenue'); SERVICE_REVENUE = 'SERVICE_REVENUE', _('Service Revenue')
        PROJECT_REVENUE = 'PROJECT_REVENUE', _('Project Revenue'); OTHER_INCOME = 'OTHER_INCOME', _('Other Income')
        COST_OF_GOODS_SOLD = 'COGS', _('Cost of Goods Sold (COGS)'); OPERATING_EXPENSE = 'OPERATING_EXPENSE', _('Operating Expense')
        SALARIES_WAGES = 'SALARIES_WAGES', _('Salaries and Wages'); RENT_EXPENSE = 'RENT_EXPENSE', _('Rent Expense')
        UTILITIES_EXPENSE = 'UTILITIES_EXPENSE', _('Utilities Expense'); DEPRECIATION = 'DEPRECIATION', _('Depreciation Expense')
        INTEREST_EXPENSE = 'INTEREST_EXPENSE', _('Interest Expense'); OTHER_EXPENSE = 'OTHER_EXPENSE', _('Other Expense')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_number = models.CharField(_("Account Number"), max_length=20, unique=True, help_text=_("Unique number identifying the account (e.g., 10100)."))
    name = models.CharField(_("Account Name"), max_length=255, help_text=_("Descriptive name of the account (e.g., 'Cash - Operating Account')."))
    account_type = models.CharField(_("Major Account Type"), max_length=20, choices=AccountType.choices, help_text=_("The main classification (Asset, Liability, Equity, Revenue, Expense)."))
    account_subtype = models.CharField(_("Account Subtype"), max_length=50, choices=AccountSubType.choices, help_text=_("Specific classification within the major type."))
    description = models.TextField(_("Description"), blank=True, null=True, help_text=_("Optional detailed description or purpose of the account."))
    parent_account = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_accounts', verbose_name=_("Parent Account"), help_text=_("Optional parent account for creating hierarchical charts."))
    is_active = models.BooleanField(_("Is Active"), default=True, help_text=_("Inactive accounts cannot be used in new transactions."))
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = _("Chart of Account"); verbose_name_plural = _("Chart of Accounts"); ordering = ['account_number', 'name']
    def __str__(self): return f"{self.account_number} - {self.name}"
    def clean(self):
        if self.parent_account and self.parent_account.pk == self.pk: raise ValidationError(_("An account cannot be its own parent."))
        super().clean()

class DisbursementVoucher(AuditableModel):
    """ Represents an authorization to disburse funds, often linked to Bills. """
    # Added PENDING_APPROVAL_2
    class DVStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING_APPROVAL = 'PENDING_APPROVAL', _('Pending Approval (L1)') # Clarified Level
        PENDING_APPROVAL_2 = 'PENDING_APPROVAL_2', _('Pending Approval (L2)') # Added L2 Pending
        APPROVED = 'APPROVED', _('Approved (Ready to Pay)')
        REJECTED = 'REJECTED', _('Rejected')
        PAID = 'PAID', _('Paid')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dv_number = models.CharField(_("DV Number"), max_length=50, unique=True, help_text=_("Unique number identifying this disbursement voucher."))
    dv_date = models.DateField(_("DV Date"), db_index=True)
    payee_name = models.CharField(_("Payee Name"), max_length=255, help_text=_("Name of the vendor, employee, or other payee."))
    amount = models.DecimalField(_("Disbursement Amount"), max_digits=15, decimal_places=2)
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Related Project"), related_name="disbursement_vouchers", help_text=_("Link to a project if this DV is specifically for it."))
    payment_method = models.CharField(_("Payment Method"), max_length=50, blank=True, help_text=_("e.g., Check, Bank Transfer, Cash"))
    check_number = models.CharField(_("Check/Reference Number"), max_length=50, blank=True, help_text=_("Check number or digital wallet transaction reference"))
    bank_account = models.ForeignKey(ChartOfAccounts, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Bank/Cash Account Disbursed From"), limit_choices_to={'is_active': True, 'account_subtype__in': [ChartOfAccounts.AccountSubType.BANK, ChartOfAccounts.AccountSubType.CASH]})
    # Updated max_length for new status
    status = models.CharField(
        _("Status"), max_length=20, choices=DVStatus.choices, # Increased max_length
        default=DVStatus.DRAFT, db_index=True
    )
    notes = models.TextField(_("Notes/Purpose"), blank=True)
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='initiated_dvs', verbose_name=_("Initiator"))
    approved_by_1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='first_approved_dvs', verbose_name=_("Approver 1"))
    approved_by_final = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='final_approved_dvs', verbose_name=_("Final Approver"))
    class Meta: verbose_name = _("Disbursement Voucher"); verbose_name_plural = _("Disbursement Vouchers"); ordering = ['-dv_date', '-dv_number']
    def __str__(self): return f"DV {self.dv_number} - {self.payee_name} ({self.amount})"

class EmployeeAdvance(AuditableModel):
    class AdvanceStatus(models.TextChoices): ISSUED = 'ISSUED', _('Issued'); PARTIALLY_LIQUIDATED = 'PARTIALLY_LIQUIDATED', _('Partially Liquidated/Repaid'); LIQUIDATED = 'LIQUIDATED', _('Fully Liquidated/Repaid'); CANCELLED = 'CANCELLED', _('Cancelled')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advance_number = models.CharField(_("Advance Number"), max_length=50, unique=True, blank=True, null=True, help_text=_("Unique number identifying this cash advance."))
    employee = models.ForeignKey('persons.Employee', on_delete=models.PROTECT, verbose_name=_("Employee"), related_name="advances")
    date_issued = models.DateField(_("Date Issued"), default=timezone.now, db_index=True)
    amount_issued = models.DecimalField(_("Amount Issued"), max_digits=15, decimal_places=2)
    purpose = models.TextField(_("Purpose"))
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Related Project"), related_name="employee_advances")
    date_due = models.DateField(_("Liquidation/Repayment Due Date"), default=get_default_advance_due_date)
    status = models.CharField(_("Status"), max_length=25, choices=AdvanceStatus.choices, default=AdvanceStatus.ISSUED, db_index=True)
    amount_liquidated = models.DecimalField(_("Amount Liquidated (Expenses)"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Portion of the advance accounted for by submitted expenses."))
    amount_repaid = models.DecimalField(_("Amount Repaid (Cash)"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Portion of the advance returned as cash by the employee."))
    asset_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, verbose_name=_("Asset Account"), null=True, blank=True, limit_choices_to={'account_subtype': ChartOfAccounts.AccountSubType.EMPLOYEE_ADVANCES}, help_text=_("The specific 'Employee Advances' asset account this pertains to."))
    class Meta: verbose_name = _("Employee Advance"); verbose_name_plural = _("Employee Advances"); ordering = ['-date_issued', 'employee']
    def __str__(self): return f"Advance {self.advance_number or self.id} for {self.employee}"
    @property
    def total_cleared(self): liq = self.amount_liquidated or Decimal('0.00'); rep = self.amount_repaid or Decimal('0.00'); return liq + rep
    @property
    def balance_remaining(self): issued = self.amount_issued or Decimal('0.00'); return issued - self.total_cleared
    @property
    def is_overdue(self):
        if self.status in [self.AdvanceStatus.LIQUIDATED, self.AdvanceStatus.CANCELLED]: return False
        if self.balance_remaining <= Decimal('0.00'): return False
        if self.date_due is None: return False
        return timezone.now().date() > self.date_due
    def clean(self):
        if self.total_cleared > (self.amount_issued or Decimal('0.00')): raise ValidationError(_("Cleared amount (Liquidated + Repaid) cannot exceed issued amount."))
        super().clean()