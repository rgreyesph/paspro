from django.contrib import admin
from .models import Tag, Address # Import your models

# Simple registration first, can customize later

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('street_line_1', 'city', 'state_province_region', 'postal_code', 'country', 'updated_at')
    search_fields = ('street_line_1', 'city', 'state_province_region', 'postal_code', 'country')
    list_filter = ('country', 'state_province_region', 'city')

# You could also use simple registration without customization:
# admin.site.register(Tag)
# admin.site.register(Address)