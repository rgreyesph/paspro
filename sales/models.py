from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from core.models import AuditableModel, Tag # Import base model and Tag
from persons.models import Customer
from projects.models import Project
from inventory.models import Product
from accounts.models import ChartOfAccounts
import uuid
from decimal import Decimal

class SalesInvoice(AuditableModel):
    """ Header for a Sales Invoice document. """
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SENT = 'SENT', _('Sent')
        PARTIAL = 'PARTIAL', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        VOID = 'VOID', _('Void')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, # Prevent deleting customer with invoices
        verbose_name=_("Customer")
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Project"), related_name="sales_invoices"
    )
    invoice_number = models.CharField(
        _("Invoice Number"), max_length=50, unique=True, # Should be unique
        help_text=_("Unique number for this invoice.")
    )
    invoice_date = models.DateField(_("Invoice Date"), db_index=True)
    due_date = models.DateField(_("Due Date"), null=True, blank=True)
    status = models.CharField(
        _("Status"), max_length=10, choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT, db_index=True
    )
    subtotal = models.DecimalField(
        _("Subtotal"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Total before taxes and discounts. Often calculated from lines.")
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Total tax amount. Often calculated.")
    )
    total_amount = models.DecimalField(
        _("Total Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Total amount due (subtotal + tax). Often calculated.")
    )
    amount_paid = models.DecimalField(
        _("Amount Paid"), max_digits=15, decimal_places=2, default=Decimal('0.00')
    )
    notes = models.TextField(_("Notes"), blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="sales_invoices")

    class Meta:
        verbose_name = _("Sales Invoice")
        verbose_name_plural = _("Sales Invoices")
        ordering = ['-invoice_date', '-invoice_number']

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.customer})"

    def calculate_totals(self):
        """ Recalculates subtotal, tax, and total from lines. """
        lines = self.lines.all()
        self.subtotal = sum(line.line_total for line in lines if line.line_total is not None)
        # Add tax calculation logic here later if needed
        # self.tax_amount = ...
        self.total_amount = self.subtotal + self.tax_amount # Adjust logic as needed
        # self.save(update_fields=['subtotal', 'tax_amount', 'total_amount']) # Be careful with recursion

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    # Consider adding validation (e.g., due_date >= invoice_date) in clean() method


class SalesInvoiceLine(models.Model):
    """ Line item detail for a Sales Invoice. """
    # No need for AuditableModel here unless tracking line item changes specifically
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        SalesInvoice, on_delete=models.CASCADE, related_name='lines',
        verbose_name=_("Sales Invoice")
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, # Can sell non-product items via description
        verbose_name=_("Product/Service"), related_name='invoice_lines'
    )
    description = models.TextField( # Allow overriding product description
        _("Description"), help_text=_("Detailed description of item/service sold.")
    )
    quantity = models.DecimalField(
        _("Quantity"), max_digits=15, decimal_places=4, default=Decimal('1.0')
    )
    unit_price = models.DecimalField(
        _("Unit Price"), max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    # Add discount fields/logic later if needed (e.g., discount_percent, discount_amount)
    line_total = models.DecimalField(
        _("Line Total"), max_digits=15, decimal_places=2, null=True, blank=True,
        help_text=_("Calculated as Quantity * Unit Price (potentially less discounts).")
    )
    # Optional: Link line item directly to a revenue account (overrides product default)
    # account = models.ForeignKey(ChartOfAccounts, on_delete=models.SET_NULL, null=True, blank=True, ...)

    class Meta:
        verbose_name = _("Sales Invoice Line")
        verbose_name_plural = _("Sales Invoice Lines")
        ordering = ['invoice', 'id'] # Order lines by their invoice and creation order

    def save(self, *args, **kwargs):
        # Calculate line total automatically
        if self.quantity is not None and self.unit_price is not None:
            self.line_total = self.quantity * self.unit_price # Add discount logic later
        super().save(*args, **kwargs)
        # Optional: Trigger recalculation of parent invoice totals after saving line
        # self.invoice.calculate_totals()
        # self.invoice.save() # Be careful with signals or overriding save to prevent infinite loops

    def __str__(self):
        return f"Line for Invoice {self.invoice.invoice_number}: {self.description[:50]}"