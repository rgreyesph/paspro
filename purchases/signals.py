from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F # For atomic updates
from inventory.models import StockLevel
from accounts.models import ChartOfAccounts # Import CoA for checking account type
from .models import BillLine, Bill

# Ensure this signal receiver is connected in purchases/apps.py

@receiver(post_save, sender=BillLine)
@receiver(post_delete, sender=BillLine)
def update_bill_totals_on_line_change(sender, instance, **kwargs):
    """
    Signal receiver to update Bill totals when a line is saved or deleted.
    """
    bill = instance.bill
    try:
        if bill and bill.pk:
            bill.calculate_totals(save=True)
    except Bill.DoesNotExist:
        pass

# --- Stock Update Signal ---
@receiver(post_save, sender=Bill)
def update_stock_on_bill_approval(sender, instance, created, update_fields, **kwargs):
    """
    Increase stock level when Bill status changes to APPROVED (indicating receipt).
    Only acts if 'status' is in update_fields or on creation if status is APPROVED.
    """
    status_updated = update_fields is not None and 'status' in update_fields
    is_approved = instance.status == Bill.BillStatus.APPROVED

    # Only increase stock ONCE when it becomes APPROVED.
    if is_approved and (created or status_updated):
        # Iterate through lines that represent inventory items being received
        inventory_lines = instance.lines.filter(
            product__isnull=False,
            product__track_inventory=True,
            warehouse__isnull=False,
            # Ensure the line account is actually an Inventory asset type
            account__account_subtype=ChartOfAccounts.AccountSubType.INVENTORY
        )
        for line in inventory_lines:
            try:
                stock_level, created_stock = StockLevel.objects.get_or_create(
                    product=line.product,
                    warehouse=line.warehouse,
                    defaults={'quantity_on_hand': Decimal('0.0')}
                )
                # Use F() expression for atomic increment
                new_quantity = F('quantity_on_hand') + line.quantity
                stock_level.quantity_on_hand = new_quantity
                stock_level.save(update_fields=['quantity_on_hand'])

            except Exception as e:
                print(f"ERROR updating stock for Bill {instance.bill_number}, Product {line.product.sku}: {e}")
                pass

    # TODO: Consider logic for VOID or status changes away from APPROVED.