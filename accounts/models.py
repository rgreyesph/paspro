from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings # For User FK
from core.models import AuditableModel # For Audit fields
import uuid

class ChartOfAccounts(models.Model):
    # ... (ChartOfAccounts model definition remains unchanged) ...
    """
    Represents an account in the company's Chart of Accounts.
    Follows standard accounting principles.
    """
    class AccountType(models.TextChoices):
        ASSET = 'ASSET', _('Asset'); LIABILITY = 'LIABILITY', _('Liability')
        EQUITY = 'EQUITY', _('Equity'); REVENUE = 'REVENUE', _('Revenue')
        EXPENSE = 'EXPENSE', _('Expense')
    class AccountSubType(models.TextChoices):
        CURRENT_ASSET = 'CURRENT_ASSET', _('Current Asset'); BANK = 'BANK', _('Bank')
        ACCOUNTS_RECEIVABLE = 'ACCOUNTS_RECEIVABLE', _('Accounts Receivable (A/R)')
        INVENTORY = 'INVENTORY', _('Inventory')
        PREPAID_EXPENSES = 'PREPAID_EXPENSES', _('Prepaid Expenses')
        OTHER_CURRENT_ASSET = 'OTHER_CURRENT_ASSET', _('Other Current Asset')
        FIXED_ASSET = 'FIXED_ASSET', _('Fixed Asset')
        CURRENT_LIABILITY = 'CURRENT_LIABILITY', _('Current Liability')
        ACCOUNTS_PAYABLE = 'ACCOUNTS_PAYABLE', _('Accounts Payable (A/P)')
        CREDIT_CARD = 'CREDIT_CARD', _('Credit Card')
        ACCRUED_LIABILITIES = 'ACCRUED_LIABILITIES', _('Accrued Liabilities')
        UNEARNED_REVENUE = 'UNEARNED_REVENUE', _('Unearned Revenue')
        LONG_TERM_LIABILITY = 'LONG_TERM_LIABILITY', _('Long-Term Liability')
        OWNERS_EQUITY = 'OWNERS_EQUITY', _("Owner's Equity")
        RETAINED_EARNINGS = 'RETAINED_EARNINGS', _('Retained Earnings')
        SALES = 'SALES', _('Sales Revenue'); SERVICE_REVENUE = 'SERVICE_REVENUE', _('Service Revenue')
        PROJECT_REVENUE = 'PROJECT_REVENUE', _('Project Revenue'); OTHER_INCOME = 'OTHER_INCOME', _('Other Income')
        COST_OF_GOODS_SOLD = 'COGS', _('Cost of Goods Sold (COGS)')
        OPERATING_EXPENSE = 'OPERATING_EXPENSE', _('Operating Expense')
        SALARIES_WAGES = 'SALARIES_WAGES', _('Salaries and Wages'); RENT_EXPENSE = 'RENT_EXPENSE', _('Rent Expense')
        UTILITIES_EXPENSE = 'UTILITIES_EXPENSE', _('Utilities Expense')
        DEPRECIATION = 'DEPRECIATION', _('Depreciation Expense')
        INTEREST_EXPENSE = 'INTEREST_EXPENSE', _('Interest Expense')
        OTHER_EXPENSE = 'OTHER_EXPENSE', _('Other Expense')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_number = models.CharField(
        _("Account Number"), max_length=20, unique=True,
        help_text=_("Unique number identifying the account (e.g., 10100).")
    )
    name = models.CharField(
        _("Account Name"), max_length=255,
        help_text=_("Descriptive name of the account (e.g., 'Cash - Operating Account').")
    )
    account_type = models.CharField(
        _("Major Account Type"), max_length=20, choices=AccountType.choices,
        help_text=_("The main classification (Asset, Liability, Equity, Revenue, Expense).")
    )
    account_subtype = models.CharField(
        _("Account Subtype"), max_length=50, choices=AccountSubType.choices,
        help_text=_("Specific classification within the major type (e.g., Bank, A/R, COGS).")
    )
    description = models.TextField(_("Description"), blank=True, null=True, help_text=_("Optional detailed description or purpose of the account."))
    parent_account = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='child_accounts', verbose_name=_("Parent Account"),
        help_text=_("Optional parent account for creating hierarchical charts.")
    )
    is_active = models.BooleanField(
        _("Is Active"), default=True, help_text=_("Inactive accounts cannot be used in new transactions.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = _("Chart of Account"); verbose_name_plural = _("Chart of Accounts"); ordering = ['account_number', 'name']
    def __str__(self): return f"{self.account_number} - {self.name}"
    def clean(self):
        if self.parent_account and self.parent_account.pk == self.pk: raise ValidationError(_("An account cannot be its own parent."))
        super().clean()

# --- New Disbursement Voucher Model ---
class DisbursementVoucher(AuditableModel):
    """ Represents an authorization to disburse funds, often linked to Bills. """
    class DVStatus(models.TextChoices):
        PREPARED = 'PREPARED', _('Prepared')
        APPROVED = 'APPROVED', _('Approved')
        PAID = 'PAID', _('Paid')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dv_number = models.CharField(
        _("DV Number"), max_length=50, unique=True,
        help_text=_("Unique number identifying this disbursement voucher.")
    )
    dv_date = models.DateField(_("DV Date"), db_index=True)
    # Payee could be generic text or linked via GenericForeignKey later
    payee_name = models.CharField(
        _("Payee Name"), max_length=255,
        help_text=_("Name of the vendor, employee, or other payee.")
    )
    # Optionally link Payee directly to Vendor or Employee if always one of them
    # vendor_payee = models.ForeignKey(Vendor, ...)
    # employee_payee = models.ForeignKey(Employee, ...)
    amount = models.DecimalField(
        _("Disbursement Amount"), max_digits=15, decimal_places=2
    )
    payment_method = models.CharField(
        _("Payment Method"), max_length=50, blank=True,
        help_text=_("e.g., Check, Bank Transfer, Cash")
    )
    check_number = models.CharField(_("Check Number"), max_length=50, blank=True)
    bank_account = models.ForeignKey( # Account funds are disbursed from
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Bank/Cash Account Disbursed From"),
        limit_choices_to={'account_subtype': ChartOfAccounts.AccountSubType.BANK} # Or Cash subtypes
    )
    status = models.CharField(
        _("Status"), max_length=10, choices=DVStatus.choices,
        default=DVStatus.PREPARED, db_index=True
    )
    notes = models.TextField(_("Notes/Purpose"), blank=True)

    class Meta:
        verbose_name = _("Disbursement Voucher")
        verbose_name_plural = _("Disbursement Vouchers")
        ordering = ['-dv_date', '-dv_number']

    def __str__(self):
        return f"DV {self.dv_number} - {self.payee_name} ({self.amount})"