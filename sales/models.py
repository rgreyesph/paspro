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
        help_text=_("Total before taxes and discounts. Calculated from lines.")
    )
    tax_amount = models.DecimalField(
        _("Tax Amount"), max_digits=15, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Total tax amount. Calculated.")
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
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="sales_invoices")

    class Meta:
        verbose_name = _("Sales Invoice")
        verbose_name_plural = _("Sales Invoices")
        ordering = ['-invoice_date', '-invoice_number']

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.customer})"

    def calculate_totals(self, save=True):
        """
        Recalculates subtotal, tax, and total from lines.
        IMPORTANT: This provides a basic structure. Real tax calculation
                   needs specific business logic (VAT rates, rules etc.)
        """
        lines = self.lines.all() # Use related_name 'lines' from SalesInvoiceLine
        new_subtotal = sum(line.line_total for line in lines if line.line_total is not None)

        # --- Placeholder Tax Calculation ---
        # Replace this with your actual tax logic based on Philippine rules.
        # This might involve checking product tax codes, customer status, etc.
        new_tax_amount = Decimal('0.00')
        # Example: Simple VAT calculation (assuming exclusive VAT)
        # tax_rate = Decimal('0.12') # Example 12% VAT
        # new_tax_amount = sum(line.line_total * tax_rate for line in lines if line.line_total is not None and line.is_vatable) # Assuming is_vatable field on line
        # --- End Placeholder ---

        new_total_amount = new_subtotal + new_tax_amount

        # Check if update is needed before saving
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
            # Save only the fields that changed to prevent recursive signals if possible
            self.save(update_fields=updated_fields)

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

class SalesInvoiceLine(models.Model):
    """ Line item detail for a Sales Invoice. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        SalesInvoice, on_delete=models.CASCADE, related_name='lines', # related_name is crucial
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
    line_total = models.DecimalField(
        _("Line Total (Exclusive of Tax)"), max_digits=15, decimal_places=2, null=True, blank=True,
        help_text=_("Calculated as Quantity * Unit Price.")
    )
    # Optional: Add fields like is_vatable if needed for line-level tax calculation
    # is_vatable = models.BooleanField(_("Is VATable?"), default=True)

    class Meta:
        verbose_name = _("Sales Invoice Line")
        verbose_name_plural = _("Sales Invoice Lines")
        ordering = ['invoice', 'id'] # Order lines by their invoice and creation order

    def save(self, *args, **kwargs):
        # Calculate line total automatically before saving
        if self.quantity is not None and self.unit_price is not None:
            self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # The post_save signal connected in signals.py will handle updating the parent invoice totals

    def __str__(self):
        return f"Line for Invoice {self.invoice.invoice_number}: {self.description[:50]}"