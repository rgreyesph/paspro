from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from core.models import AuditableModel, Tag
from persons.models import Customer
from projects.models import Project
from inventory.models import Product
from accounts.models import ChartOfAccounts
import uuid
from decimal import Decimal

def get_default_invoice_due_date():
    """ Returns the date 30 days from now. """
    return timezone.now().date() + timedelta(days=30)

class SalesInvoice(AuditableModel):
    """ Header for a Sales Invoice document. """
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft'); SENT = 'SENT', _('Sent')
        SHIPPED = 'SHIPPED', _('Shipped'); PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Paid'); VOID = 'VOID', _('Void')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name=_("Customer"))
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Project"), related_name="sales_invoices")
    invoice_number = models.CharField(_("Invoice Number"), max_length=50, unique=True, help_text=_("Unique number for this invoice."))
    invoice_date = models.DateField(_("Invoice Date"), default=timezone.now, db_index=True)
    due_date = models.DateField(_("Due Date"), default=get_default_invoice_due_date) # Use default
    status = models.CharField(_("Status"), max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated from lines."))
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated."))
    total_amount = models.DecimalField(_("Total Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated."))
    # Changed verbose_name
    amount_paid = models.DecimalField(
        _("Amount Received"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Updated automatically by payments.")
    )
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="sales_invoices")
    class Meta: verbose_name = _("Sales Invoice"); verbose_name_plural = _("Sales Invoices"); ordering = ['-invoice_date', '-invoice_number']
    def __str__(self): return f"Invoice {self.invoice_number} ({self.customer})"

    def calculate_totals(self, save=True):
        lines = self.lines.all()
        new_subtotal = sum(line.line_total for line in lines if line.line_total is not None)

        # Basic 12% Exclusive VAT Calculation (adjust rate/logic as needed)
        tax_rate = Decimal('0.12')
        vatable_total = sum(
            line.line_total for line in lines
            if line.line_total is not None and not line.is_vat_exempt
        )
        new_tax_amount = vatable_total * tax_rate
        new_total_amount = new_subtotal + new_tax_amount

        # Ensure comparisons are between Decimals
        current_subtotal = self.subtotal or Decimal('0.00')
        current_tax = self.tax_amount or Decimal('0.00')
        current_total = self.total_amount or Decimal('0.00')

        updated_fields = []
        # Use quantize for consistent decimal comparison
        if current_subtotal.compare(new_subtotal.quantize(Decimal('0.01'))) != 0:
             self.subtotal = new_subtotal; updated_fields.append('subtotal')
        if current_tax.compare(new_tax_amount.quantize(Decimal('0.01'))) != 0:
             self.tax_amount = new_tax_amount; updated_fields.append('tax_amount')
        if current_total.compare(new_total_amount.quantize(Decimal('0.01'))) != 0:
             self.total_amount = new_total_amount; updated_fields.append('total_amount')

        if save and updated_fields:
            self.save(update_fields=updated_fields)
        return bool(updated_fields)

    @property
    def balance_due(self):
        total = self.total_amount or Decimal('0.00')
        paid = self.amount_paid or Decimal('0.00')
        return total - paid

    def update_payment_status(self, save=True):
        total_paid = self.payments_received.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        new_amount_paid = total_paid
        new_status = self.status
        if self.status not in [self.InvoiceStatus.VOID, self.InvoiceStatus.DRAFT]:
            current_total = self.total_amount or Decimal('0.00')
            # Ensure balance calculation uses Decimal
            balance = current_total - new_amount_paid.quantize(Decimal('0.01'))

            if balance <= Decimal('0.00') and current_total > Decimal('0.00'):
                new_status = self.InvoiceStatus.PAID
            elif new_amount_paid > Decimal('0.00') and balance > Decimal('0.00'):
                 new_status = self.InvoiceStatus.PARTIAL
            elif new_amount_paid == Decimal('0.00'):
                 if self.status in [self.InvoiceStatus.PARTIAL, self.InvoiceStatus.PAID]:
                     new_status = self.InvoiceStatus.SHIPPED if self.status == self.InvoiceStatus.SHIPPED else self.InvoiceStatus.SENT

        updated_fields = []
        # Ensure comparison uses Decimal
        current_paid = self.amount_paid or Decimal('0.00')
        if current_paid.compare(new_amount_paid.quantize(Decimal('0.01'))) != 0:
            self.amount_paid = new_amount_paid
            updated_fields.append('amount_paid')
        if self.status != new_status:
            self.status = new_status
            updated_fields.append('status')

        if save and updated_fields:
            self.save(update_fields=updated_fields)
        return bool(updated_fields)

class SalesInvoiceLine(models.Model):
    """ Line item detail for a Sales Invoice. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Sales Invoice"))
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Product/Service"), related_name='invoice_lines')
    # Make description optional (blank=True)
    description = models.TextField(_("Description"), blank=True, help_text=_("Detailed description of item/service sold (fills from product if blank)."))
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Source Warehouse"), limit_choices_to={'is_active': True}, help_text=_("Warehouse stock is drawn from (for inventory items)."))
    quantity = models.DecimalField(_("Quantity"), max_digits=15, decimal_places=4, default=Decimal('1.0'))
    unit_price = models.DecimalField(_("Unit Price"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    line_total = models.DecimalField(_("Line Total (Exclusive of Tax)"), max_digits=15, decimal_places=2, null=True, blank=True, help_text=_("Calculated as Quantity * Unit Price."))
    # Added VAT exemption flag
    is_vat_exempt = models.BooleanField(_("VAT Exempt?"), default=False, help_text=_("Check if this line item is exempt from VAT calculation."))

    class Meta: verbose_name = _("Sales Invoice Line"); verbose_name_plural = _("Sales Invoice Lines"); ordering = ['invoice', 'id']

    def save(self, *args, **kwargs):
        if not self.description and self.product: self.description = self.product.name # Autofill description
        if self.quantity is not None and self.unit_price is not None: self.line_total = self.quantity * self.unit_price
        if self.product and self.product.track_inventory and not self.warehouse: raise ValidationError({'warehouse': _("Warehouse must be selected for inventory item '%(product)s'.") % {'product': self.product.name}})
        if self.product and not self.product.track_inventory: self.warehouse = None
        super().save(*args, **kwargs)

    def __str__(self): return f"Line for Invoice {self.invoice.invoice_number}: {self.description[:50]}"