from django.contrib import admin
from import_export.admin import ImportExportModelAdmin # Import
from .models import Project

@admin.register(Project)
class ProjectAdmin(ImportExportModelAdmin): # Inherit
    list_display = ('name', 'project_code', 'customer', 'status', 'start_date', 'end_date', 'budget', 'created_by')
    list_filter = ('status', 'customer', 'tags')
    search_fields = ('name', 'project_code', 'description', 'customer__name')
    # Make audit fields read-only
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    filter_horizontal = ('tags',)
    date_hierarchy = 'start_date'
    autocomplete_fields = ('customer', 'created_by', 'updated_by') # Use autocomplete

    # Explicit fieldsets to ensure audit fields are shown
    fieldsets = (
        (None, {'fields': ('name', 'project_code', 'customer', 'status', 'description')}),
        ('Dates & Budget', {'fields': ('start_date', 'end_date', 'budget')}),
        ('Categorization', {'fields': ('tags',)}),
        ('Auditing', {'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')}),
    )

    def save_model(self, request, obj, form, change):
        """ Auto-populate audit fields """
        if not obj.pk: # If creating new
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)