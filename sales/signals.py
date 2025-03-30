from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import SalesInvoiceLine, SalesInvoice

# Ensure this signal receiver is connected in sales/apps.py

@receiver(post_save, sender=SalesInvoiceLine)
@receiver(post_delete, sender=SalesInvoiceLine)
def update_invoice_totals_on_line_change(sender, instance, **kwargs):
    """
    Signal receiver to update SalesInvoice totals when a line is saved or deleted.
    """
    # instance is the SalesInvoiceLine that was saved or deleted
    # Access the related invoice via the ForeignKey relationship
    invoice_to_update = instance.invoice

    # Call the calculation method on the invoice instance
    # Pass save=True to ensure the invoice is saved after recalculation
    invoice_to_update.calculate_totals(save=True)