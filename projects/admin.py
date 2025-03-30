from django.contrib import admin
from .models import Project

# Register your models here.
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project_code', 'customer', 'status', 'start_date', 'end_date', 'budget')
    list_filter = ('status', 'customer', 'tags')
    search_fields = ('name', 'project_code', 'description', 'customer__name')
    raw_id_fields = ('customer',) # Use search popup for customer selection
    filter_horizontal = ('tags',)
    date_hierarchy = 'start_date' # Add quick date navigation