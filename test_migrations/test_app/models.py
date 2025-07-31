"""
Test models that demonstrate the BEFORE and AFTER states.
"""

from django.db import models


# BEFORE: What your migration looked like without the fix
class BusinessWithoutFix(models.Model):
    """Shows what Business migration looked like before the fix."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    model_type = models.CharField(max_length=100, db_index=True, editable=False)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Businesses Without Fix"

    def __str__(self):
        return self.name


class BusinessExtensionWithoutFix(BusinessWithoutFix):
    """Shows what BusinessExtension looked like before fix - creates separate table."""

    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Business Extensions Without Fix"

    def __str__(self):
        return self.name


# AFTER: What your migration should look like with the fix
class BusinessWithFix(models.Model):
    """Shows what Business migration looks like with the fix."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    model_type = models.CharField(max_length=100, db_index=True, editable=False)
    name = models.CharField(max_length=255)
    # Note: description field is added here for all subclasses (STI)
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Businesses With Fix"

    def __str__(self):
        return self.name


class BusinessExtensionWithFix(BusinessWithFix):
    """Shows what BusinessExtension looks like with fix - proxy model, no separate table."""

    class Meta:
        proxy = True  # This is the key difference!
        verbose_name_plural = "Business Extensions With Fix"

    def __str__(self):
        return self.name
