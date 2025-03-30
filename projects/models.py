from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
# Removed direct import: from persons.models import Customer
from core.models import Tag, AuditableModel # Import base model
import uuid

class Project(AuditableModel): # Inherit from AuditableModel
    """ Represents a specific project undertaken for a customer or internally. """
    class ProjectStatus(models.TextChoices): PLANNING = 'PLANNING', _('Planning'); ACTIVE = 'ACTIVE', _('Active'); ON_HOLD = 'ON_HOLD', _('On Hold'); COMPLETED = 'COMPLETED', _('Completed'); CANCELLED = 'CANCELLED', _('Cancelled')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Project Name"), max_length=255)
    project_code = models.CharField(_("Project Code"), max_length=50, unique=True, blank=True, null=True, help_text=_("Unique code for internal tracking."))
    description = models.TextField(_("Description"), blank=True)
    # Use STRING notation 'persons.Customer' to avoid circular import
    customer = models.ForeignKey(
        'persons.Customer',
        on_delete=models.PROTECT, # Prevent deleting customer if they have projects
        null=True, # Allow internal projects without a customer
        blank=True,
        verbose_name=_("Customer"),
        related_name="projects"
    )
    status = models.CharField(_("Status"), max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PLANNING)
    start_date = models.DateField(_("Start Date"), null=True, blank=True)
    end_date = models.DateField(_("End Date"), null=True, blank=True, help_text=_("Planned or actual completion date."))
    budget = models.DecimalField(_("Budget Amount"), max_digits=15, decimal_places=2, null=True, blank=True, help_text=_("Estimated or allocated budget for the project."))
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("Tags"), related_name="projects")
    # Audit fields (created_at, updated_at, created_by, updated_by) are inherited from AuditableModel

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        ordering = ['-start_date', 'name'] # Order by most recent start date, then name

    def __str__(self):
        return f"{self.name} ({self.project_code or 'No Code'})"

    def clean(self):
        # Add validation, e.g., end_date should not be before start_date
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(_("End date cannot be before start date."))
        super().clean()