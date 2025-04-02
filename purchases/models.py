from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum # For summing payments
from core.models import AuditableModel, Tag
from persons.models import Vendor
from projects.models import Project
# from inventory.models import Product, Warehouse
from inventory.models import Product
from accounts.models import ChartOfAccounts, DisbursementVoucher
import uuid
from decimal import Decimal

class Bill(AuditableModel):
    """ Header for a Bill received from a Vendor. """
    class BillStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SUBMITTED = 'SUBMITTED', _('Submitted for Approval')
        APPROVED = 'APPROVED', _('Approved for Payment/Receipt') # Trigger for stock
        PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        VOID = 'VOID', _('Void')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, verbose_name=_("Vendor"))
    bill_number = models.CharField(_("Vendor Bill Number"), max_length=100, help_text=_("The invoice/reference number from the vendor."))
    bill_date = models.DateField(_("Bill Date"), db_index=True)
    due_date = models.DateField(_("Due Date"), null=True, blank=True)
    disbursement_voucher = models.ForeignKey(DisbursementVoucher, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Disbursement Voucher"), related_name="bills")
    status = models.CharField(_("Status"), max_length=10, choices=BillStatus.choices, default=BillStatus.DRAFT, db_index=True)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated from lines."))
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated from lines."))
    total_amount = models.DecimalField(_("Total Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated."))
    amount_paid = models.DecimalField(_("Amount Paid"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Updated automatically by payments.")) # Help text updated
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="bills")

    class Meta: verbose_name = _("Bill / Vendor Expense"); verbose_name_plural = _("Bills / Vendor Expenses"); ordering = ['-bill_date', '-bill_number']; constraints = [models.UniqueConstraint(fields=['vendor', 'bill_number'], name='unique_vendor_bill_number')]
    def __str__(self): return f"Bill {self.bill_number} from {self.vendor}"

    def calculate_totals(self, save=True):
        lines = self.lines.all()
        new_subtotal = sum(line.line_total for line in lines if line.line_total is not None)
        # Placeholder Tax Calculation
        new_tax_amount = sum(line.calculate_tax() for line in lines)
        new_total_amount = new_subtotal + new_tax_amount
        updated_fields = []
        if self.subtotal != new_subtotal: self.subtotal = new_subtotal; updated_fields.append('subtotal')
        if self.tax_amount != new_tax_amount: self.tax_amount = new_tax_amount; updated_fields.append('tax_amount')
        if self.total_amount != new_total_amount: self.total_amount = new_total_amount; updated_fields.append('total_amount')
        if save and updated_fields: self.save(update_fields=updated_fields)
        return bool(updated_fields)

    @property
    def balance_due(self):
        total = self.total_amount or Decimal('0.00')
        paid = self.amount_paid or Decimal('0.00')
        return total - paid

    def update_payment_status(self, save=True):
        """ Recalculates amount_paid and updates status based on balance. """
        # Sum amounts from related 'payments_made' (related_name from PaymentMade.bills M2M)
        total_paid = self.payments_made.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        new_amount_paid = total_paid

        # Determine new status
        new_status = self.status
        if self.status not in [self.BillStatus.VOID, self.BillStatus.DRAFT, self.BillStatus.SUBMITTED]: # Don't auto-update early stages
            current_total = self.total_amount or Decimal('0.00')
            balance = current_total - new_amount_paid

            if balance <= Decimal('0.00') and current_total > Decimal('0.00'):
                new_status = self.BillStatus.PAID
            elif new_amount_paid > Decimal('0.00') and balance > Decimal('0.00'):
                 new_status = self.BillStatus.PARTIAL
            elif new_amount_paid == Decimal('0.00'):
                 # Revert to APPROVED if fully unpaid?
                 if self.status in [self.BillStatus.PARTIAL, self.BillStatus.PAID]:
                     new_status = self.BillStatus.APPROVED

        # Check if updates are needed
        updated_fields = []
        if self.amount_paid != new_amount_paid:
            self.amount_paid = new_amount_paid
            updated_fields.append('amount_paid')
        if self.status != new_status:
            self.status = new_status
            updated_fields.append('status')

        if save and updated_fields:
            self.save(update_fields=updated_fields)
        return bool(updated_fields)

class BillLine(models.Model):
    """ Line item detail for a Bill. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Bill"))
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Product/Service"), related_name='bill_lines')
    description = models.TextField(_("Description"), help_text=_("Detailed description of item/service purchased."))
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, verbose_name=_("Expense/Asset Account"), related_name='bill_lines', limit_choices_to={'is_active': True, 'account_type__in': [ChartOfAccounts.AccountType.EXPENSE, ChartOfAccounts.AccountType.ASSET]})
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Project"), related_name="expense_lines")
    # --- Add Warehouse Field ---
    warehouse = models.ForeignKey(
        'inventory.Warehouse', # Use string notation
        on_delete=models.SET_NULL,
        null=True, blank=True, # Make optional, only needed for inventory items
        verbose_name=_("Destination Warehouse"),
        limit_choices_to={'is_active': True},
        help_text=_("Warehouse stock is received into (for inventory items).")
    )
    # --- End Warehouse Field ---
    quantity = models.DecimalField(_("Quantity"), max_digits=15, decimal_places=4, default=Decimal('1.0'))
    unit_price = models.DecimalField(_("Unit Price"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    line_total = models.DecimalField(_("Line Total (Exclusive of Tax)"), max_digits=15, decimal_places=2, null=True, blank=True, help_text=_("Calculated as Quantity * Unit Price."))
    is_vatable = models.BooleanField(_("Is VATable?"), default=True, help_text=_("Check if this line item is subject to Value Added Tax."))
    bir_classification = models.CharField(_("BIR Classification/ATC"), max_length=100, blank=True, help_text=_("BIR Alphanumeric Tax Code (ATC) or classification, if applicable."))

    class Meta: verbose_name = _("Bill Line"); verbose_name_plural = _("Bill Lines"); ordering = ['bill', 'id']

    def save(self, *args, **kwargs):
        if self.quantity is not None and self.unit_price is not None: self.line_total = self.quantity * self.unit_price
        # Validation: Ensure warehouse is selected if product tracks inventory and account is Inventory Asset
        is_inventory_purchase = self.account and self.account.account_subtype == ChartOfAccounts.AccountSubType.INVENTORY
        if self.product and self.product.track_inventory and is_inventory_purchase and not self.warehouse:
             raise ValidationError({
                 'warehouse': _("Warehouse must be selected when purchasing inventory item '%(product)s' into an Inventory account.") % {'product': self.product.name}
             })
        # Clear warehouse if not relevant
        if not (self.product and self.product.track_inventory and is_inventory_purchase):
            self.warehouse = None
        super().save(*args, **kwargs)

    def calculate_tax(self, tax_rate=Decimal('0.12')):
        if self.is_vatable and self.line_total is not None: return self.line_total * tax_rate
        return Decimal('0.00')
    def __str__(self): return f"Line for Bill {self.bill.bill_number}: {self.description[:50]}"