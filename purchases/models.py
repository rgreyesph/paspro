from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from core.models import AuditableModel, Tag
from persons.models import Vendor
from projects.models import Project
from inventory.models import Product
from accounts.models import ChartOfAccounts, DisbursementVoucher # Import DV
import uuid
from decimal import Decimal

class Bill(AuditableModel):
    """ Header for a Bill received from a Vendor. """
    class BillStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SUBMITTED = 'SUBMITTED', _('Submitted for Approval')
        APPROVED = 'APPROVED', _('Approved for Payment')
        PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        VOID = 'VOID', _('Void')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.PROTECT, # Prevent deleting vendor with bills
        verbose_name=_("Vendor")
    )
    # Removed project link from header, will use line item link primarily
    # project = models.ForeignKey(Project, ...)
    bill_number = models.CharField(
        _("Vendor Bill Number"), max_length=100,
        help_text=_("The invoice/reference number from the vendor.")
    )
    bill_date = models.DateField(_("Bill Date"), db_index=True)
    due_date = models.DateField(_("Due Date"), null=True, blank=True)
    disbursement_voucher = models.ForeignKey( # Link to DV
        DisbursementVoucher, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Disbursement Voucher"), related_name="bills"
    )
    status = models.CharField(
        _("Status"), max_length=10, choices=BillStatus.choices,
        default=BillStatus.DRAFT, db_index=True
    )
    subtotal = models.DecimalField(
        _("Subtotal"), max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        _("Total Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    amount_paid = models.DecimalField( # Track payments made against this bill
        _("Amount Paid"), max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="bills")

    class Meta:
        verbose_name = _("Bill / Vendor Expense")
        verbose_name_plural = _("Bills / Vendor Expenses")
        ordering = ['-bill_date', '-bill_number']
        # Unique constraint for vendor + bill_number can be useful
        constraints = [
            models.UniqueConstraint(fields=['vendor', 'bill_number'], name='unique_vendor_bill_number')
        ]

    def __str__(self):
        return f"Bill {self.bill_number} from {self.vendor}"

    def calculate_totals(self):
        """ Recalculates subtotal, tax, and total from lines. """
        lines = self.lines.all()
        self.subtotal = sum(line.line_total for line in lines if line.line_total is not None)
        # Add tax calculation based on lines (e.g., sum of tax per line if applicable)
        self.tax_amount = sum(line.calculate_tax() for line in lines) # Assumes calculate_tax method exists on line
        self.total_amount = self.subtotal + self.tax_amount
        # self.save(update_fields=['subtotal', 'tax_amount', 'total_amount']) # Careful with recursion

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid


class BillLine(models.Model):
    """ Line item detail for a Bill. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name='lines',
        verbose_name=_("Bill")
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Product/Service"), related_name='bill_lines'
    )
    description = models.TextField(
        _("Description"), help_text=_("Detailed description of item/service purchased.")
    )
    account = models.ForeignKey( # The Expense or Asset account being debited
        ChartOfAccounts, on_delete=models.PROTECT, # Must select an account
        verbose_name=_("Expense/Asset Account"), related_name='bill_lines',
        limit_choices_to={'is_active': True, 'account_type__in': [
            ChartOfAccounts.AccountType.EXPENSE, ChartOfAccounts.AccountType.ASSET # Allow inventory/asset purchases
        ]}
    )
    project = models.ForeignKey( # Link expense line to a specific project
        Project, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Project"), related_name="expense_lines"
    )
    quantity = models.DecimalField(
        _("Quantity"), max_digits=15, decimal_places=4, default=Decimal('1.0')
    )
    unit_price = models.DecimalField(
        _("Unit Price"), max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    line_total = models.DecimalField(
        _("Line Total"), max_digits=15, decimal_places=2, null=True, blank=True,
        help_text=_("Calculated as Quantity * Unit Price.")
    )
    is_vatable = models.BooleanField( # Simple VAT flag per line
        _("Is VATable?"), default=True,
        help_text=_("Check if this line item is subject to Value Added Tax.")
    )
    bir_classification = models.CharField( # BIR Code
        _("BIR Classification/ATC"), max_length=100, blank=True,
        help_text=_("BIR Alphanumeric Tax Code (ATC) or classification, if applicable.")
    )

    class Meta:
        verbose_name = _("Bill Line")
        verbose_name_plural = _("Bill Lines")
        ordering = ['bill', 'id']

    def save(self, *args, **kwargs):
        if self.quantity is not None and self.unit_price is not None:
            self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Optional: Trigger recalculation of parent bill totals
        # self.bill.calculate_totals()
        # self.bill.save() # Careful with signals/save overrides

    def calculate_tax(self, tax_rate=Decimal('0.12')): # Example VAT Rate
        """ Calculate tax for this line if applicable. """
        if self.is_vatable and self.line_total is not None:
            # Tax calculation logic depends heavily on specific rules (inclusive/exclusive)
            # Assuming exclusive VAT for this example:
            return self.line_total * tax_rate
        return Decimal('0.00')

    def __str__(self):
        return f"Line for Bill {self.bill.bill_number}: {self.description[:50]}"