from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Project

@admin.register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    list_display = ('name', 'project_code', 'customer', 'status', 'start_date', 'end_date', 'budget', 'get_created_by_username')
    list_filter = ('status', 'customer', 'tags')
    search_fields = ('name', 'project_code', 'description', 'customer__name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by', 'get_created_by_username', 'get_updated_by_username')
    filter_horizontal = ('tags',)
    date_hierarchy = 'start_date'
    autocomplete_fields = ('customer',)

    def get_fieldsets(self, request, obj=None):
        base_fieldsets = [
            (None, {'fields': ('name', 'project_code', 'customer', 'status', 'description')}),
            ('Dates & Budget', {'fields': ('start_date', 'end_date', 'budget')}),
            ('Categorization', {'fields': ('tags',)}),
        ]
        audit_fields = ['created_at', 'get_created_by_username', 'updated_at', 'get_updated_by_username']
        base_fieldsets.append(('Auditing', {'fields': audit_fields}))
        return base_fieldsets

    @admin.display(description='Created By')
    def get_created_by_username(self, obj): return obj.created_by.username if obj.created_by else None
    @admin.display(description='Updated By')
    def get_updated_by_username(self, obj): return obj.updated_by.username if obj.updated_by else None

    # --- Revised save_model logic ---
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            obj.created_by = request.user
            obj.save(update_fields=['created_by'])
    # --- End revised logic ---