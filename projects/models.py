from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from persons.models import Customer # Import Customer model
from core.models import Tag # Import Tag model
import uuid

# Create your models here.

class Project(models.Model):
    """ Represents a specific project undertaken for a customer or internally. """

    class ProjectStatus(models.TextChoices):
        PLANNING = 'PLANNING', _('Planning')
        ACTIVE = 'ACTIVE', _('Active')
        ON_HOLD = 'ON_HOLD', _('On Hold')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        _("Project Name"),
        max_length=255
    )
    project_code = models.CharField(
        _("Project Code"),
        max_length=50,
        unique=True,
        blank=True, # Can be optional or auto-generated later
        null=True,
        help_text=_("Unique code for internal tracking.")
    )
    description = models.TextField(
        _("Description"),
        blank=True
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT, # Prevent deleting customer if they have projects
        null=True, # Allow internal projects without a customer
        blank=True,
        verbose_name=_("Customer"),
        related_name="projects"
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNING
    )
    start_date = models.DateField(
        _("Start Date"),
        null=True,
        blank=True
    )
    end_date = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Planned or actual completion date.")
    )
    budget = models.DecimalField(
        _("Budget Amount"),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Estimated or allocated budget for the project.")
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        verbose_name=_("Tags"),
        related_name="projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        ordering = ['-start_date', 'name'] # Order by most recent start date, then name

    def __str__(self):
        return f"{self.name} ({self.project_code or 'No Code'})"

    # Potential future methods:
    # def get_total_expenses(self):
    #     # Logic to sum related expense line items
    #     pass
    #
    # def get_profitability(self):
    #     # Logic to calculate revenue vs expenses for the project
    #     pass
    #
    # def clean(self):
    #     # Add validation, e.g., end_date should not be before start_date
    #     if self.start_date and self.end_date and self.end_date < self.start_date:
    #         raise models.ValidationError(_("End date cannot be before start date."))
    #     super().clean()