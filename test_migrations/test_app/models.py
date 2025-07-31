"""
Test models for STI migration generation.
"""

from django.db import models

from django_sti_models import TypedModel, TypeField


class AugendModel(TypedModel):
    model_type = TypeField()

    class Meta:
        abstract = True


class Business(AugendModel):
    """Concrete STI base model - inherits TypeField from abstract AugendModel."""

    name = models.CharField(max_length=255)
    # The TypeField is inherited from AugendModel automatically

    class Meta:
        verbose_name_plural = "Businesses"
        app_label = "test_app"
        # Do NOT set abstract = True - this must be concrete!

    def __str__(self):
        return self.name


class BusinessExtension(Business):
    """STI subclass - should automatically become proxy model."""

    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Business Extensions"
        app_label = "test_app"

    def __str__(self):
        return self.name
