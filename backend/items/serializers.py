from rest_framework import serializers

from .models import PublishedItem


class PublishedItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishedItem
        fields = (
            "id",
            "slug",
            "title",
            "description",
            "document_type",
            "status",
            "page_count",
            "created_at",
            "processed_at",
        )
        read_only_fields = fields
