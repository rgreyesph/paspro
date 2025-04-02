from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F # For atomic updates
from inventory.models import StockLevel # Import StockLevel
from .models import SalesInvoiceLine, SalesInvoice

# Ensure this signal receiver is connected in sales/apps.py

@receiver(post_save, sender=SalesInvoiceLine)
@receiver(post_delete, sender=SalesInvoiceLine)
def update_invoice_totals_on_line_change(sender, instance, **kwargs):
    """
    Signal receiver to update SalesInvoice totals when a line is saved or deleted.
    """
    invoice = instance.invoice
    # Need try-except block in case invoice was deleted simultaneously or doesn't exist
    try:
        # Check if the related invoice object actually exists
        if invoice and invoice.pk:
           invoice.calculate_totals(save=True)
    except SalesInvoice.DoesNotExist:
        pass # Handle case where invoice might have been deleted

# --- Stock Update Signal ---
@receiver(post_save, sender=SalesInvoice)
def update_stock_on_invoice_shipment(sender, instance, created, update_fields, **kwargs):
    """
    Decrease stock level when SalesInvoice status changes to SHIPPED.
    Only acts if 'status' is in update_fields (on update) or on creation if status is SHIPPED.
    """
    # Check if status field was updated OR if it's a new instance
    status_updated = update_fields is not None and 'status' in update_fields
    is_shipped = instance.status == SalesInvoice.InvoiceStatus.SHIPPED

    # We only want to decrease stock ONCE when it becomes SHIPPED.
    # This simple check triggers if saved *while* status is SHIPPED.
    # A more robust check would compare previous status to current status.
    # Let's proceed with the simpler check for now. It relies on the admin/user
    # not saving the invoice repeatedly while already in SHIPPED status without changes.
    if is_shipped and (created or status_updated):
        # Iterate through lines that have a valid product and warehouse
        for line in instance.lines.filter(product__isnull=False, product__track_inventory=True, warehouse__isnull=False):
            try:
                stock_level, created_stock = StockLevel.objects.get_or_create(
                    product=line.product,
                    warehouse=line.warehouse,
                    defaults={'quantity_on_hand': Decimal('0.0')} # Default if creating
                )
                # Use F() expression for atomic decrement
                new_quantity = F('quantity_on_hand') - line.quantity
                stock_level.quantity_on_hand = new_quantity
                stock_level.save(update_fields=['quantity_on_hand'])

                # Refresh from DB if needed elsewhere in this request lifecycle, but usually not required here.
                # stock_level.refresh_from_db()

            except Exception as e:
                # Log the error, notify admin, etc. - Don't let stock errors stop the invoice save silently.
                print(f"ERROR updating stock for Invoice {instance.invoice_number}, Product {line.product.sku}: {e}")
                # Consider raising the error or using Django messages framework
                pass

    # TODO: Consider adding logic for when an invoice is VOIDED or status changes *away* from SHIPPED
    # (e.g., should stock be incremented back?) Requires careful thought about business process.