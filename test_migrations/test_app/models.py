"""
Test models that replicate your exact use case.
"""
from django.db import models
from django_sti_models import TypedModel, TypeField


class AugendModel(TypedModel):
    """Abstract base model with TypeField - simulates your AugendModel."""
    model_type = TypeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Business(AugendModel):
    """Concrete business model - simulates your Business model."""
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name


class BusinessExtension(Business):
    """Business extension - simulates your BusinessExtension model."""
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return self.name