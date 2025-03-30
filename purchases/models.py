from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError # Import
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
        _("Subtotal"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Total before tax. Calculated from lines.")
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Total tax amount. Calculated from lines.")
    )
    total_amount = models.DecimalField(
        _("Total Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Total amount due (subtotal + tax). Calculated.")
    )
    # This field might be updated manually or via payment linking logic later
    amount_paid = models.DecimalField(
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

    def calculate_totals(self, save=True):
        """
        Recalculates subtotal, tax, and total from lines.
        Needs specific tax logic for BIR compliance.
        """
        lines = self.lines.all() # Use related_name 'lines' from BillLine
        new_subtotal = sum(line.line_total for line in lines if line.line_total is not None)

        # --- Placeholder Tax Calculation ---
        # Replace with actual Philippine BIR tax logic (VAT, EWT etc.)
        # This likely involves checking bir_classification, is_vatable on lines, vendor status etc.
        new_tax_amount = sum(line.calculate_tax() for line in lines) # Assumes line method exists
        # --- End Placeholder ---

        new_total_amount = new_subtotal + new_tax_amount

        updated_fields = []
        if self.subtotal != new_subtotal:
            self.subtotal = new_subtotal
            updated_fields.append('subtotal')
        if self.tax_amount != new_tax_amount:
            self.tax_amount = new_tax_amount
            updated_fields.append('tax_amount')
        if self.total_amount != new_total_amount:
            self.total_amount = new_total_amount
            updated_fields.append('total_amount')

        if save and updated_fields:
            self.save(update_fields=updated_fields)

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid


class BillLine(models.Model):
    """ Line item detail for a Bill. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name='lines', # related_name is crucial
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
        _("Line Total (Exclusive of Tax)"), max_digits=15, decimal_places=2, null=True, blank=True,
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
        # Calculate line total automatically before saving
        if self.quantity is not None and self.unit_price is not None:
            self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # The post_save signal connected in signals.py will handle updating the parent bill totals

    def calculate_tax(self, tax_rate=Decimal('0.12')):
        """
        Placeholder for calculating tax for this line.
        Requires actual BIR logic (VAT, EWT based on ATC etc.)
        """
        if self.is_vatable and self.line_total is not None:
            # Example assumes 12% VAT, exclusive calculation
            # Replace with real logic based on bir_classification etc.
            return self.line_total * tax_rate
        return Decimal('0.00')

    def __str__(self):
        return f"Line for Bill {self.bill.bill_number}: {self.description[:50]}"