from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings # Import settings
import uuid

# --- Auditable Base Model ---
class AuditableModel(models.Model):
    """
    Abstract base model providing audit fields (created/updated by/at).
    """
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
        editable=False # Should not be editable in forms
    )
    updated_at = models.DateTimeField(
        _("Updated At"),
        auto_now=True,
        editable=False # Should not be editable in forms
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Allow blank until auto-population is implemented
        related_name='%(app_label)s_%(class)s_created_by',
        verbose_name=_("Created By"),
        # editable=False # Keep editable=True until auto-population logic is added
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Allow blank until auto-population is implemented
        related_name='%(app_label)s_%(class)s_updated_by',
        verbose_name=_("Updated By"),
        # editable=False # Keep editable=True until auto-population logic is added
    )

    class Meta:
        abstract = True # Make this an abstract base class
        ordering = ['-updated_at'] # Default ordering by most recently updated


# --- Existing Core Models ---
class Tag(models.Model):
    # ... (Tag model definition remains unchanged) ...
    """
    A centrally managed Tag that can be applied to various records
    like Transactions, Projects, Customers, Vendors, etc. for reporting.
    """
    name = models.CharField(
        _("Tag Name"), max_length=100, unique=True,
        help_text=_("Unique name for the tag.")
    )
    description = models.TextField(
        _("Description"), blank=True, help_text=_("Optional description for the tag.")
    )
    # Note: We could make Tag inherit AuditableModel too if needed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ['name']

    def __str__(self):
        return self.name

class Address(models.Model):
    # ... (Address model definition remains unchanged) ...
    """
    Represents a physical address. Can be linked from Employee, Vendor, Customer, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    street_line_1 = models.CharField(_("Street Line 1"), max_length=255)
    street_line_2 = models.CharField(
        _("Street Line 2"), max_length=255, blank=True,
        help_text=_("Apartment, suite, unit, building, floor, etc.")
    )
    city = models.CharField(_("City / Municipality"), max_length=100)
    state_province_region = models.CharField(
        _("State / Province / Region"), max_length=100, blank=True
    )
    postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True)
    country = models.CharField(_("Country"), max_length=100, default="Philippines")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self):
        parts = [
            self.street_line_1, self.street_line_2, self.city,
            self.state_province_region, self.postal_code, self.country
        ]
        return ", ".join(filter(None, parts))

    @property
    def full_address(self):
        lines = [self.street_line_1]
        if self.street_line_2: lines.append(self.street_line_2)
        city_state_zip = filter(None, [self.city, self.state_province_region])
        lines.append(f"{' '.join(city_state_zip)} {self.postal_code or ''}".strip())
        if self.country: lines.append(self.country)
        return "\n".join(filter(None, lines))