from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import PaymentReceived, PaymentMade
from sales.models import SalesInvoice # Need the related models
from purchases.models import Bill

# Use a set to prevent recursive signals if update_payment_status saves the invoice/bill again
# This is a simple mechanism; more robust solutions might involve thread locals or disabling signals temporarily.
# Note: This might not be strictly necessary if update_payment_status only saves when changes occur.
processing_updates = set()

@receiver(m2m_changed, sender=PaymentReceived.invoices.through)
def update_invoice_payment_status_on_m2m_change(sender, instance, action, pk_set, **kwargs):
    """
    Update related SalesInvoice(s) when PaymentReceived.invoices M2M changes.
    instance = PaymentReceived object
    pk_set = set of primary keys for SalesInvoice objects added/removed
    """
    global processing_updates

    # Check if we are already processing to prevent potential recursion
    if instance.pk in processing_updates:
        return

    if action in ["post_add", "post_remove", "post_clear"]:
        processing_updates.add(instance.pk) # Mark as processing
        try:
            if action == "post_clear":
                # If all invoices are cleared, we might need to find which ones *were* linked before clearing.
                # This is complex. For simplicity, let's assume clearing means recalculating potentially affected invoices,
                # or perhaps handle this manually/via specific actions if clearing is common.
                # A simpler approach is to only react to add/remove.
                pass # Skip post_clear for now
            else:
                # Get all invoices related to this payment *after* the change OR
                # Get invoices involved in *this* change (pk_set)
                # It's safer to recalculate all currently linked invoices
                invoices_to_update = instance.invoices.all()
                for invoice in invoices_to_update:
                    invoice.update_payment_status(save=True)

                # If items were removed, we also need to update the ones that were just removed.
                if action == "post_remove":
                    removed_invoices = SalesInvoice.objects.filter(pk__in=pk_set)
                    for invoice in removed_invoices:
                        # Need try-except in case the invoice was deleted simultaneously
                        try:
                           invoice.update_payment_status(save=True)
                        except SalesInvoice.DoesNotExist:
                           pass

        finally:
            processing_updates.remove(instance.pk) # Unmark as processing


@receiver(m2m_changed, sender=PaymentMade.bills.through)
def update_bill_payment_status_on_m2m_change(sender, instance, action, pk_set, **kwargs):
    """
    Update related Bill(s) when PaymentMade.bills M2M changes.
    instance = PaymentMade object
    pk_set = set of primary keys for Bill objects added/removed
    """
    global processing_updates

    if instance.pk in processing_updates:
        return

    if action in ["post_add", "post_remove", "post_clear"]:
        processing_updates.add(instance.pk)
        try:
            if action == "post_clear":
                pass # Skip post_clear for simplicity
            else:
                # Recalculate all currently linked bills
                bills_to_update = instance.bills.all()
                for bill in bills_to_update:
                    bill.update_payment_status(save=True)

                # Also update bills that were just removed
                if action == "post_remove":
                    removed_bills = Bill.objects.filter(pk__in=pk_set)
                    for bill in removed_bills:
                        try:
                            bill.update_payment_status(save=True)
                        except Bill.DoesNotExist:
                            pass
        finally:
             processing_updates.remove(instance.pk)

# Note: You might also need post_save/post_delete signals on PaymentReceived/PaymentMade themselves
# if deleting a payment or changing its amount should also trigger updates on related documents.