from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Project

@admin.register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    list_display = ('name', 'project_code', 'customer', 'status', 'start_date', 'end_date', 'budget', 'get_created_by_full_name') # Use full name display method
    list_filter = ('status', 'customer', 'tags')
    search_fields = ('name', 'project_code', 'description', 'customer__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by', 'get_created_by_full_name', 'get_updated_by_full_name') # Use full name display method
    filter_horizontal = ('tags',)
    date_hierarchy = 'start_date'
    autocomplete_fields = ('customer',)

    def get_fieldsets(self, request, obj=None):
        base_fieldsets = [
            (None, {'fields': ('name', 'project_code', 'customer', 'status', 'description')}),
            ('Dates & Budget', {'fields': ('start_date', 'end_date', 'budget')}),
            ('Categorization', {'fields': ('tags',)}),
        ]
        # Use display methods for audit info
        audit_fields = ['created_at', 'get_created_by_full_name', 'updated_at', 'get_updated_by_full_name']
        base_fieldsets.append(('Auditing', {'fields': audit_fields}))
        return base_fieldsets

    # Use full name methods
    @admin.display(description='Created By')
    def get_created_by_full_name(self, obj): return obj.created_by.get_full_name() if obj.created_by else None
    @admin.display(description='Updated By')
    def get_updated_by_full_name(self, obj): return obj.updated_by.get_full_name() if obj.updated_by else None

    def save_model(self, request, obj, form, change):
        is_new = not change
        if is_new: obj.initiator = request.user # Project doesn't have initiator yet, ok
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if is_new:
            obj.created_by = request.user
            update_list = ['created_by']
            # if 'initiator' in [f.name for f in obj._meta.fields]: update_list.append('initiator')
            obj.save(update_fields=update_list)