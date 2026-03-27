from django.contrib import admin

from items.models import PublishedItem


@admin.register(PublishedItem)
class PublishedItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "status",
        "page_count",
        "created_at",
        "processed_at",
    )
    list_filter = ("status",)
    search_fields = ("title", "slug", "id")
    readonly_fields = ("id", "created_at", "processed_at", "page_count", "error_message")
