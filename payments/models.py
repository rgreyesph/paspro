from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from core.models import AuditableModel, Tag
from persons.models import Customer, Vendor, Employee # Import persons
from sales.models import SalesInvoice
from purchases.models import Bill
from accounts.models import ChartOfAccounts, DisbursementVoucher
from persons.models import EmployeeAdvance # Import EmployeeAdvance
import uuid
from decimal import Decimal

class PaymentReceived(AuditableModel):
    """ Records payments received from customers. """
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', _('Cash')
        CHECK = 'CHECK', _('Check')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        CREDIT_CARD = 'CREDIT_CARD', _('Credit Card Payment')
        OTHER = 'OTHER', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, verbose_name=_("Customer Received From")
    )
    payment_date = models.DateField(_("Payment Date"), db_index=True)
    amount = models.DecimalField(_("Amount Received"), max_digits=15, decimal_places=2)
    payment_method = models.CharField(
        _("Payment Method"), max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER
    )
    reference_number = models.CharField( # e.g., Check number, Transaction ID
        _("Reference Number"), max_length=100, blank=True
    )
    account_deposited_to = models.ForeignKey( # Bank/Cash account where money went
        ChartOfAccounts, on_delete=models.PROTECT, verbose_name=_("Account Deposited To"),
        limit_choices_to={'is_active': True, 'account_subtype__in': [
            ChartOfAccounts.AccountSubType.BANK,
            # Add other cash-like asset subtypes if necessary
            ChartOfAccounts.AccountSubType.OTHER_CURRENT_ASSET,
            ChartOfAccounts.AccountSubType.CURRENT_ASSET, # broader category if needed
        ]}
    )
    # Link to invoices paid by this payment
    invoices = models.ManyToManyField(
        SalesInvoice, blank=True, verbose_name=_("Related Sales Invoices"), related_name="payments_received"
    )
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="payments_received")

    class Meta:
        verbose_name = _("Payment Received")
        verbose_name_plural = _("Payments Received")
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment from {self.customer} ({self.amount}) on {self.payment_date}"
    # TODO later: Add logic/signal to update SalesInvoice.amount_paid when linked

class PaymentMade(AuditableModel):
    """ Records payments made to vendors, employees, etc. """
    class PayeeType(models.TextChoices):
        VENDOR = 'VENDOR', _('Vendor')
        EMPLOYEE = 'EMPLOYEE', _('Employee')
        OTHER = 'OTHER', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_date = models.DateField(_("Payment Date"), db_index=True)
    amount = models.DecimalField(_("Amount Paid"), max_digits=15, decimal_places=2)
    payee_type = models.CharField(
        _("Payee Type"), max_length=10, choices=PayeeType.choices
    )
    # Link to specific payee based on type (Consider GenericForeignKey later if complex)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, null=True, blank=True, verbose_name=_("Vendor Payee"),
        related_name="payments_made"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, null=True, blank=True, verbose_name=_("Employee Payee"),
        related_name="payments_made"
    )
    other_payee_name = models.CharField( # For PayeeType OTHER
        _("Other Payee Name"), max_length=255, blank=True
    )
    payment_method = models.CharField(
        _("Payment Method"), max_length=20, choices=PaymentReceived.PaymentMethod.choices, # Reuse choices
        default=PaymentReceived.PaymentMethod.BANK_TRANSFER
    )
    reference_number = models.CharField(_("Reference Number"), max_length=100, blank=True)
    account_paid_from = models.ForeignKey( # Bank/Cash account money came from
        ChartOfAccounts, on_delete=models.PROTECT, verbose_name=_("Account Paid From"),
        limit_choices_to={'is_active': True, 'account_subtype__in': [
            ChartOfAccounts.AccountSubType.BANK,
            # Add other cash-like asset subtypes if necessary
        ]}
    )
    # Link to Bills paid / DVs settled
    bills = models.ManyToManyField(
        Bill, blank=True, verbose_name=_("Related Bills Paid"), related_name="payments_made"
    )
    disbursement_voucher = models.ForeignKey( # Can link directly to the authorizing DV
        DisbursementVoucher, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Related Disbursement Voucher"), related_name="payments_made"
    )
    # Can link to an Employee Advance being issued (if not using DV)
    # Or link to repayment from employee (less common here, usually in PaymentReceived)
    employee_advance_issued = models.ForeignKey(
        EmployeeAdvance, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Related Employee Advance Issued"), related_name="payments_made_for_advance"
    )
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="payments_made")

    class Meta:
        verbose_name = _("Payment Made")
        verbose_name_plural = _("Payments Made")
        ordering = ['-payment_date']

    def __str__(self):
        payee = self.get_payee_name()
        return f"Payment to {payee} ({self.amount}) on {self.payment_date}"

    def get_payee_name(self):
        if self.payee_type == self.PayeeType.VENDOR and self.vendor: return str(self.vendor)
        if self.payee_type == self.PayeeType.EMPLOYEE and self.employee: return str(self.employee)
        if self.payee_type == self.PayeeType.OTHER: return self.other_payee_name or "Other"
        return "N/A"

    def clean(self): # Basic validation based on payee type
        payee_count = sum(f is not None for f in [self.vendor, self.employee, self.other_payee_name])
        if self.payee_type == self.PayeeType.VENDOR and not self.vendor:
             raise ValidationError(_("Vendor must be selected for Vendor payee type."))
        if self.payee_type == self.PayeeType.EMPLOYEE and not self.employee:
             raise ValidationError(_("Employee must be selected for Employee payee type."))
        if self.payee_type == self.PayeeType.OTHER and not self.other_payee_name:
             raise ValidationError(_("Other Payee Name must be provided for Other payee type."))
        # Ensure exactly one payee is specified based on type
        if self.payee_type == self.PayeeType.VENDOR and payee_count > 1:
            raise ValidationError(_("Provide only Vendor for Vendor payee type."))
        if self.payee_type == self.PayeeType.EMPLOYEE and payee_count > 1:
            raise ValidationError(_("Provide only Employee for Employee payee type."))
        if self.payee_type == self.PayeeType.OTHER and payee_count > 1:
             raise ValidationError(_("Provide only Other Payee Name for Other payee type."))
        super().clean()
    # TODO later: Add logic/signal to update Bill.amount_paid or Advance status when linked