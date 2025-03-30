from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from core.models import Address, Tag # Import shared models
from accounts.models import ChartOfAccounts # Import CoA
import uuid
from decimal import Decimal # Import Decimal for quantity

# Create your models here.

class Warehouse(models.Model):
    """ Represents a physical location where inventory is stored. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        _("Warehouse Name"),
        max_length=150,
        unique=True
    )
    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Warehouse Address")
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Can inventory be stored/retrieved from this warehouse?")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Warehouse")
        verbose_name_plural = _("Warehouses")
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """ Defines a product or service the company buys, sells, or uses. """

    class ProductType(models.TextChoices):
        INVENTORY = 'INVENTORY', _('Inventory Item') # Track quantity & COGS
        SERVICE = 'SERVICE', _('Service') # Non-physical, no quantity tracking needed usually
        NON_INVENTORY = 'NON_INVENTORY', _('Non-Inventory Item') # Items bought/expensed, not tracked

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Product/Service Name"), max_length=255)
    sku = models.CharField(
        _("SKU (Stock Keeping Unit)"),
        max_length=100,
        unique=True,
        blank=True, # Allow generating later if needed
        null=True,
        help_text=_("Unique code identifying the product.")
    )
    description = models.TextField(_("Description"), blank=True)
    product_type = models.CharField(
        _("Product Type"),
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.INVENTORY,
        help_text=_("Determines how the item is tracked and accounted for.")
    )
    track_inventory = models.BooleanField(
        _("Track Inventory Quantity"),
        default=True,
        help_text=_("Should stock levels be tracked for this item? Usually True for Inventory types.")
    )
    unit_cost = models.DecimalField(
        _("Default Unit Cost"),
        max_digits=15,
        decimal_places=2, # Adjust decimal places as needed for precision
        null=True,
        blank=True,
        help_text=_("Default or standard cost per unit. Actual cost may vary (FIFO/LIFO/Avg).")
    )
    sales_price = models.DecimalField(
        _("Sales Price"),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Default selling price per unit.")
    )
    income_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Default Income Account"),
        related_name='income_products',
        limit_choices_to={'account_type': ChartOfAccounts.AccountType.REVENUE},
        help_text=_("Account to credit when this item is sold.")
    )
    expense_cogs_account = models.ForeignKey(
        ChartOfAccounts,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Default Expense/COGS Account"),
        related_name='expense_products',
        limit_choices_to={'account_type__in': [
            ChartOfAccounts.AccountType.EXPENSE,
            # Include COGS subtype if explicitly defined, otherwise just Expense
            # ChartOfAccounts.AccountSubType.COST_OF_GOODS_SOLD
        ]},
        help_text=_("Account to debit for Cost of Goods Sold (if Inventory) or Expense (if Non-Inventory/Service bought).")
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Inactive products cannot be bought or sold.")
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        verbose_name=_("Tags"),
        related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product / Service")
        verbose_name_plural = _("Products & Services")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku or 'No SKU'})"

    def clean(self):
        # Automatically set track_inventory based on type if not explicitly set? Risky.
        # Better to enforce consistency: If type is INVENTORY, track_inventory should generally be True.
        if self.product_type == self.ProductType.INVENTORY and not self.track_inventory:
            # Optionally raise ValidationError or just set it automatically?
            # Let's keep it flexible for now, user might have edge cases.
            pass
        if self.product_type != self.ProductType.INVENTORY and self.track_inventory:
             raise ValidationError(
                 _("Inventory tracking should only be enabled for 'Inventory Item' product types.")
             )
        super().clean()


class StockLevel(models.Model):
    """ Tracks the quantity of a specific Product in a specific Warehouse. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE, # If product is deleted, its stock levels don't make sense
        verbose_name=_("Product"),
        limit_choices_to={'track_inventory': True}, # Only allow trackable products
        related_name="stock_levels"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE, # If warehouse is deleted, its stock levels are gone
        verbose_name=_("Warehouse"),
        limit_choices_to={'is_active': True}, # Only stock in active warehouses
        related_name="stock_levels"
    )
    quantity_on_hand = models.DecimalField(
        _("Quantity on Hand"),
        max_digits=15,
        decimal_places=4, # Allow for fractional quantities if needed (e.g., kg, liters)
        default=Decimal('0.0')
    )
    reorder_point = models.DecimalField(
        _("Reorder Point"),
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text=_("Quantity at which reordering should be considered.")
    )
    last_stock_update = models.DateTimeField(
        _("Last Stock Update"),
        auto_now=True, # Automatically update when saved
        help_text=_("Timestamp of the last modification to this stock level record.")
    )
    # Note: Actual stock movements (in/out) will be recorded via separate Transaction models later.
    # This model represents the *current snapshot*.

    class Meta:
        verbose_name = _("Stock Level")
        verbose_name_plural = _("Stock Levels")
        # Ensure that there's only one record per product per warehouse
        constraints = [
            models.UniqueConstraint(fields=['product', 'warehouse'], name='unique_product_warehouse_stock')
        ]
        ordering = ['warehouse', 'product']

    def __str__(self):
        return f"{self.product} in {self.warehouse}: {self.quantity_on_hand}"

    # clean method to ensure product.track_inventory is True? Already handled by limit_choices_to.
    # def clean(self):
    #     if not self.product.track_inventory:
    #         raise ValidationError(_("Cannot track stock level for a product that does not track inventory."))
    #     super().clean()