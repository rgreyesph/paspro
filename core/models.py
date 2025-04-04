from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid

# --- Auditable Base Model ---
class AuditableModel(models.Model):
    """
    Abstract base model providing audit fields (created/updated by/at).
    """
    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
        editable=False # Keep editable=False for timestamps
    )
    updated_at = models.DateTimeField(
        _("Updated At"),
        auto_now=True,
        editable=False # Keep editable=False for timestamps
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created_by',
        verbose_name=_("Created By"),
        # editable=False # Removed
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated_by',
        verbose_name=_("Updated By"),
        # editable=False # Removed
    )

    class Meta:
        abstract = True
        ordering = ['-updated_at']


# --- Existing Core Models ---
class Tag(models.Model):
    """
    A centrally managed Tag that can be applied to various records
    like Transactions, Projects, Customers, Vendors, etc. for reporting.
    """
    name = models.CharField(
        _("Tag Name"),
        max_length=100,
        unique=True, # Ensures tag names are unique
        help_text=_("Unique name for the tag.")
    )
    description = models.TextField(
        _("Description"),
        blank=True, # Optional field
        help_text=_("Optional description for the tag.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ['name'] # Default order tags alphabetically

    def __str__(self):
        """String representation of the Tag object."""
        return self.name

class Address(models.Model):
    """
    Represents a physical address. Can be linked from Employee, Vendor, Customer, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    street_line_1 = models.CharField(
        _("Street Line 1"),
        max_length=255
    )
    street_line_2 = models.CharField(
        _("Street Line 2"),
        max_length=255,
        blank=True, # Optional
        help_text=_("Apartment, suite, unit, building, floor, etc.")
    )
    city = models.CharField(
        _("City / Municipality"),
        max_length=100
    )
    state_province_region = models.CharField(
        _("State / Province / Region"),
        max_length=100,
        blank=True # Optional depending on country
    )
    postal_code = models.CharField(
        _("Postal Code"),
        max_length=20,
        blank=True # Optional depending on country
    )
    country = models.CharField(
        _("Country"),
        max_length=100,
        default="Philippines" # Sensible default, could use django-countries later
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self):
        """String representation of the Address object."""
        parts = [
            self.street_line_1,
            self.street_line_2,
            self.city,
            self.state_province_region,
            self.postal_code,
            self.country
        ]
        # Filter out blank parts and join with commas
        return ", ".join(filter(None, parts))

    @property
    def full_address(self):
        """Returns a formatted multi-line address string."""
        # --- Corrected Syntax ---
        lines = []
        if self.street_line_1:
            lines.append(self.street_line_1)
        if self.street_line_2:
            lines.append(self.street_line_2)

        city_state_parts = filter(None, [self.city, self.state_province_region])
        city_state_line = " ".join(city_state_parts)

        postal_part = self.postal_code or ""

        # Combine city/state/zip, handling potential spaces
        city_state_zip = f"{city_state_line} {postal_part}".strip()
        if city_state_zip: # Avoid adding an empty line if all parts are blank
             lines.append(city_state_zip)

        if self.country:
            lines.append(self.country)

        return "\n".join(lines)
        # --- End Corrected Syntax ---