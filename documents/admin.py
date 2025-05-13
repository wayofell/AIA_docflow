from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'file_format', 'upload_date', 'size')
    list_filter = ('file_format', 'upload_date')
    search_fields = ('title', 'text_content')
    readonly_fields = ('upload_date', 'size', 'text_content')
    fieldsets = (
        (None, {
            'fields': ('title', 'file', 'file_format')
        }),
        ('Metadata', {
            'fields': ('upload_date', 'size')
        }),
        ('Content', {
            'fields': ('text_content',)
        }),
    )
