import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        ENDED = "ended", "Ended"

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(choices=Status.choices, default=Status.DRAFT, max_length=16)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=("draft", "scheduled", "live", "ended")),
                name="campaign_status_is_valid",
            ),
        ]

    def __str__(self):
        return self.name


class Offer(models.Model):
    class Type(models.TextChoices):
        PRODUCT_PERCENT_DISCOUNT = "PRODUCT_PERCENT_DISCOUNT", "Product percent discount"
        CART_FIXED_DISCOUNT = "CART_FIXED_DISCOUNT", "Cart fixed discount"
        STICKER_EARN = "STICKER_EARN", "Sticker earn"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="offers")
    type = models.CharField(choices=Type.choices, max_length=32)
    parameters = models.JSONField(default=dict)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position", "id")

    def __str__(self):
        return self.get_type_display()

    def clean(self):
        super().clean()

        from looplink.campaigns.services.offers import offer_parameter_errors

        errors = offer_parameter_errors(self.type, self.parameters)
        if errors:
            raise ValidationError({"parameters": errors})


class Enrollment(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="enrollments")
    submitted_identity = models.CharField(max_length=254)
    normalized_identity = models.CharField(max_length=254)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("campaign", "normalized_identity"),
                name="unique_campaign_normalized_identity",
            ),
        ]

    def __str__(self):
        return f"Enrollment for {self.campaign_id}"
