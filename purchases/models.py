from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.conf import settings
from core.models import AuditableModel, Tag
from persons.models import Vendor
from projects.models import Project
from inventory.models import Product
from accounts.models import ChartOfAccounts, DisbursementVoucher
import uuid
from decimal import Decimal

class Bill(AuditableModel):
    """ Header for a Bill received from a Vendor. """
    # Revised Status Choices for Approval Workflow
    class BillStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING_APPROVAL = 'PENDING_APPROVAL', _('Pending Approval (L1)') # Clarified Level
        PENDING_APPROVAL_2 = 'PENDING_APPROVAL_2', _('Pending Approval (L2)') # Added L2 Pending
        APPROVED = 'APPROVED', _('Approved (Ready to Pay/Received)')
        REJECTED = 'REJECTED', _('Rejected')
        PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        VOID = 'VOID', _('Void')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, verbose_name=_("Vendor"))
    bill_number = models.CharField(_("Vendor Bill Number"), max_length=100, help_text=_("The invoice/reference number from the vendor."))
    bill_date = models.DateField(_("Bill Date"), db_index=True)
    due_date = models.DateField(_("Due Date"), null=True, blank=True)
    disbursement_voucher = models.ForeignKey(DisbursementVoucher, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Disbursement Voucher"), related_name="bills")
    # Updated status choices, max_length and default
    status = models.CharField(
        _("Status"), max_length=20, choices=BillStatus.choices, # Increased max_length
        default=BillStatus.DRAFT, db_index=True
    )
    subtotal = models.DecimalField(_("Subtotal"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated from lines."))
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated from lines."))
    total_amount = models.DecimalField(_("Total Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated."))
    amount_paid = models.DecimalField(_("Amount Paid"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Updated automatically by payments."))
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="bills")
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='initiated_bills', verbose_name=_("Initiator"))
    approved_by_1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='first_approved_bills', verbose_name=_("Approver 1"))
    approved_by_final = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='final_approved_bills', verbose_name=_("Final Approver"))

    class Meta: verbose_name = _("Bill / Vendor Expense"); verbose_name_plural = _("Bills / Vendor Expenses"); ordering = ['-bill_date', '-bill_number']; constraints = [models.UniqueConstraint(fields=['vendor', 'bill_number'], name='unique_vendor_bill_number')]
    def __str__(self): return f"Bill {self.bill_number} from {self.vendor}"

    def calculate_totals(self, save=True):
        lines = self.lines.all(); new_subtotal = sum(line.line_total for line in lines if line.line_total is not None); new_tax_amount = sum(line.calculate_tax() for line in lines); new_total_amount = new_subtotal + new_tax_amount
        updated_fields = []; current_subtotal = self.subtotal or Decimal('0.00'); current_tax = self.tax_amount or Decimal('0.00'); current_total = self.total_amount or Decimal('0.00')
        if current_subtotal.compare(new_subtotal.quantize(Decimal('0.01'))) != 0: self.subtotal = new_subtotal; updated_fields.append('subtotal')
        if current_tax.compare(new_tax_amount.quantize(Decimal('0.01'))) != 0: self.tax_amount = new_tax_amount; updated_fields.append('tax_amount')
        if current_total.compare(new_total_amount.quantize(Decimal('0.01'))) != 0: self.total_amount = new_total_amount; updated_fields.append('total_amount')
        if save and updated_fields: self.save(update_fields=updated_fields)
        return bool(updated_fields)

    @property
    def balance_due(self): total = self.total_amount or Decimal('0.00'); paid = self.amount_paid or Decimal('0.00'); return total - paid

    def update_payment_status(self, save=True):
        total_paid = self.payments_made.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'); new_amount_paid = total_paid; new_status = self.status
        # Don't automatically change status if it's in a pre-approved or rejected/void state
        if self.status not in [self.BillStatus.DRAFT, self.BillStatus.PENDING_APPROVAL, self.BillStatus.PENDING_APPROVAL_2, self.BillStatus.REJECTED, self.BillStatus.VOID]:
            current_total = self.total_amount or Decimal('0.00'); balance = current_total - new_amount_paid.quantize(Decimal('0.01'))
            if balance <= Decimal('0.00') and current_total > Decimal('0.00'): new_status = self.BillStatus.PAID
            elif new_amount_paid > Decimal('0.00') and balance > Decimal('0.00'): new_status = self.BillStatus.PARTIAL
            elif new_amount_paid == Decimal('0.00'):
                 if self.status in [self.BillStatus.PARTIAL, self.BillStatus.PAID]: new_status = self.BillStatus.APPROVED # Revert to APPROVED if fully unpaid
        updated_fields = []; current_paid = self.amount_paid or Decimal('0.00')
        if current_paid.compare(new_amount_paid.quantize(Decimal('0.01'))) != 0: self.amount_paid = new_amount_paid; updated_fields.append('amount_paid')
        if self.status != new_status: self.status = new_status; updated_fields.append('status')
        if save and updated_fields: self.save(update_fields=updated_fields)
        return bool(updated_fields)

class BillLine(models.Model): # ... (No changes needed here) ...
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False); bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Bill")); product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Product/Service"), related_name='bill_lines'); description = models.TextField(_("Description"), help_text=_("Detailed description of item/service purchased.")); account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, verbose_name=_("Expense/Asset Account"), related_name='bill_lines', limit_choices_to={'is_active': True, 'account_type__in': [ChartOfAccounts.AccountType.EXPENSE, ChartOfAccounts.AccountType.ASSET]}); project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Project"), related_name="expense_lines"); warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Destination Warehouse"), limit_choices_to={'is_active': True}, help_text=_("Warehouse stock is received into (for inventory items).")); quantity = models.DecimalField(_("Quantity"), max_digits=15, decimal_places=4, default=Decimal('1.0')); unit_price = models.DecimalField(_("Unit Price"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))]); line_total = models.DecimalField(_("Line Total (Exclusive of Tax)"), max_digits=15, decimal_places=2, null=True, blank=True, help_text=_("Calculated as Quantity * Unit Price.")); is_vatable = models.BooleanField(_("Is VATable?"), default=True, help_text=_("Check if this line item is subject to Value Added Tax.")); bir_classification = models.CharField(_("BIR Classification/ATC"), max_length=100, blank=True, help_text=_("BIR Alphanumeric Tax Code (ATC) or classification, if applicable."))
    class Meta: verbose_name = _("Bill Line"); verbose_name_plural = _("Bill Lines"); ordering = ['bill', 'id']
    def save(self, *args, **kwargs):
        if self.quantity is not None and self.unit_price is not None: self.line_total = self.quantity * self.unit_price
        is_inventory_purchase = self.account and self.account.account_subtype == ChartOfAccounts.AccountSubType.INVENTORY
        if self.product and self.product.track_inventory and is_inventory_purchase and not self.warehouse: raise ValidationError({'warehouse': _("Warehouse must be selected when purchasing inventory item '%(product)s' into an Inventory account.") % {'product': self.product.name}})
        if not (self.product and self.product.track_inventory and is_inventory_purchase): self.warehouse = None
        super().save(*args, **kwargs)
    def calculate_tax(self, tax_rate=Decimal('0.12')):
        if self.is_vatable and self.line_total is not None: return self.line_total * tax_rate
        return Decimal('0.00')
    def __str__(self): return f"Line for Bill {self.bill.bill_number}: {self.description[:50]}"