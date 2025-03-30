from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BillLine, Bill

# Ensure this signal receiver is connected in purchases/apps.py

@receiver(post_save, sender=BillLine)
@receiver(post_delete, sender=BillLine)
def update_bill_totals_on_line_change(sender, instance, **kwargs):
    """
    Signal receiver to update Bill totals when a line is saved or deleted.
    """
    # instance is the BillLine that was saved or deleted
    bill_to_update = instance.bill

    # Call the calculation method on the bill instance
    bill_to_update.calculate_totals(save=True) # Pass save=True