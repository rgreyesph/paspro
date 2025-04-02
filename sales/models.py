from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.db.models import Sum # For summing payments
from core.models import AuditableModel, Tag
from persons.models import Customer
from projects.models import Project
# Use string notation for Warehouse to potentially avoid future circular issues if needed
# from inventory.models import Product, Warehouse
from inventory.models import Product
import uuid
from decimal import Decimal

class SalesInvoice(AuditableModel):
    """ Header for a Sales Invoice document. """
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SENT = 'SENT', _('Sent')
        SHIPPED = 'SHIPPED', _('Shipped') # Added status for stock trigger
        PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        VOID = 'VOID', _('Void')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name=_("Customer"))
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Project"), related_name="sales_invoices")
    invoice_number = models.CharField(_("Invoice Number"), max_length=50, unique=True, help_text=_("Unique number for this invoice."))
    invoice_date = models.DateField(_("Invoice Date"), db_index=True)
    due_date = models.DateField(_("Due Date"), null=True, blank=True)
    status = models.CharField(_("Status"), max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated from lines."))
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated."))
    total_amount = models.DecimalField(_("Total Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Calculated."))
    amount_paid = models.DecimalField(_("Amount Paid"), max_digits=15, decimal_places=2, default=Decimal('0.00'), help_text=_("Updated automatically by payments.")) # Help text updated
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="sales_invoices")

    class Meta: verbose_name = _("Sales Invoice"); verbose_name_plural = _("Sales Invoices"); ordering = ['-invoice_date', '-invoice_number']
    def __str__(self): return f"Invoice {self.invoice_number} ({self.customer})"

    def calculate_totals(self, save=True):
        lines = self.lines.all()
        new_subtotal = sum(line.line_total for line in lines if line.line_total is not None)
        # Placeholder Tax Calculation
        new_tax_amount = Decimal('0.00')
        new_total_amount = new_subtotal + new_tax_amount
        updated_fields = []
        if self.subtotal != new_subtotal: self.subtotal = new_subtotal; updated_fields.append('subtotal')
        if self.tax_amount != new_tax_amount: self.tax_amount = new_tax_amount; updated_fields.append('tax_amount')
        if self.total_amount != new_total_amount: self.total_amount = new_total_amount; updated_fields.append('total_amount')
        if save and updated_fields: self.save(update_fields=updated_fields)
        # Return True if totals were changed, False otherwise (useful for signals)
        return bool(updated_fields)

    @property
    def balance_due(self):
        # Ensure total_amount is not None
        total = self.total_amount or Decimal('0.00')
        paid = self.amount_paid or Decimal('0.00')
        return total - paid

    def update_payment_status(self, save=True):
        """ Recalculates amount_paid and updates status based on balance. """
        # Sum amounts from related 'payments_received' (related_name from PaymentReceived.invoices M2M)
        total_paid = self.payments_received.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        new_amount_paid = total_paid

        # Determine new status based on amounts
        new_status = self.status # Default to current status
        if self.status not in [self.InvoiceStatus.VOID, self.InvoiceStatus.DRAFT]: # Don't auto-update VOID/DRAFT based on payment
            # Recalculate balance using the potentially new amount_paid
            current_total = self.total_amount or Decimal('0.00')
            balance = current_total - new_amount_paid

            if balance <= Decimal('0.00') and current_total > Decimal('0.00'):
                new_status = self.InvoiceStatus.PAID
            elif new_amount_paid > Decimal('0.00') and balance > Decimal('0.00'):
                 new_status = self.InvoiceStatus.PARTIAL
            elif new_amount_paid == Decimal('0.00'):
                 # Revert to SENT or SHIPPED if fully unpaid? Choose desired logic.
                 # Let's assume SENT is the base state after DRAFT if unpaid.
                 # If previously SHIPPED, maybe keep it SHIPPED? Requires tracking previous state.
                 # Simplest for now: if unpaid, revert to SENT if it was PARTIAL/PAID.
                 if self.status in [self.InvoiceStatus.PARTIAL, self.InvoiceStatus.PAID]:
                     new_status = self.InvoiceStatus.SENT # Or SHIPPED if applicable?

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


class SalesInvoiceLine(models.Model):
    """ Line item detail for a Sales Invoice. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Sales Invoice"))
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Product/Service"), related_name='invoice_lines')
    description = models.TextField(_("Description"), help_text=_("Detailed description of item/service sold."))
    # --- Add Warehouse Field ---
    warehouse = models.ForeignKey(
        'inventory.Warehouse', # Use string notation
        on_delete=models.SET_NULL,
        null=True, blank=True, # Make optional, only needed for inventory items
        verbose_name=_("Source Warehouse"),
        limit_choices_to={'is_active': True},
        help_text=_("Warehouse stock is drawn from (for inventory items).")
    )
    # --- End Warehouse Field ---
    quantity = models.DecimalField(_("Quantity"), max_digits=15, decimal_places=4, default=Decimal('1.0'))
    unit_price = models.DecimalField(_("Unit Price"), max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    line_total = models.DecimalField(_("Line Total (Exclusive of Tax)"), max_digits=15, decimal_places=2, null=True, blank=True, help_text=_("Calculated as Quantity * Unit Price."))

    class Meta: verbose_name = _("Sales Invoice Line"); verbose_name_plural = _("Sales Invoice Lines"); ordering = ['invoice', 'id']

    def save(self, *args, **kwargs):
        if self.quantity is not None and self.unit_price is not None: self.line_total = self.quantity * self.unit_price
        # Validation: Ensure warehouse is selected if product tracks inventory
        if self.product and self.product.track_inventory and not self.warehouse:
             raise ValidationError({
                 'warehouse': _("Warehouse must be selected for inventory item '%(product)s'.") % {'product': self.product.name}
             })
        # Clear warehouse if product doesn't track inventory
        if self.product and not self.product.track_inventory:
            self.warehouse = None
        super().save(*args, **kwargs)

    def __str__(self): return f"Line for Invoice {self.invoice.invoice_number}: {self.description[:50]}"