#!/usr/bin/env python
"""
Test the STI solution with the user's exact model structure.
"""

import os
import sys
import django
from django.conf import settings

# Configure minimal Django
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        USE_TZ=True,
        INSTALLED_APPS=['django_sti_models'],
    )

django.setup()

# Import after Django setup
from django.db import models, connection
from django_sti_models import TypedModel, TypeField

# Mock the AugendModel and other dependencies
class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

# Your exact AugendModel
class AugendModel(TypedModel):
    model_type = TypeField()

    class Meta:
        abstract = True

# Your exact Business model
class Business(AugendModel):
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name

# Your exact BusinessExtension model
class BusinessExtension(Business):
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return self.name

def test_sti_solution():
    """Test that the STI solution works correctly."""
    print("🧪 Testing STI Solution with User's Model Structure\n")
    
    # Check that Business is set up as STI base
    print("📝 Checking Business model:")
    assert hasattr(Business._meta, 'is_sti_base'), "Business should be marked as STI base"
    assert Business._meta.is_sti_base, "Business should be marked as STI base"
    print("  ✅ Business is marked as STI base")
    
    assert hasattr(Business._meta, 'type_field_name'), "Business should have type_field_name"
    assert Business._meta.type_field_name == 'model_type', "Type field name should be 'model_type'"
    print("  ✅ Business has type_field_name")
    
    assert hasattr(Business._meta, 'typed_models'), "Business should have typed_models registry"
    assert 'Business' in Business._meta.typed_models, "Business should be in typed_models"
    print("  ✅ Business has typed_models registry")
    
    # Check that BusinessExtension is set up as STI subclass
    print("\n📝 Checking BusinessExtension model:")
    assert hasattr(BusinessExtension._meta, 'is_sti_subclass'), "BusinessExtension should be marked as STI subclass"
    assert BusinessExtension._meta.is_sti_subclass, "BusinessExtension should be marked as STI subclass"
    print("  ✅ BusinessExtension is marked as STI subclass")
    
    assert BusinessExtension._meta.proxy, "BusinessExtension should be a proxy model"
    print("  ✅ BusinessExtension is a proxy model")
    
    assert BusinessExtension._meta.sti_base_model == Business, "BusinessExtension should point to Business as base"
    print("  ✅ BusinessExtension points to Business as base")
    
    # Check that it's registered with the base
    assert 'BusinessExtension' in Business._meta.typed_models, "BusinessExtension should be registered"
    print("  ✅ BusinessExtension is registered with Business")
    
    # Test creating instances
    print("\n📝 Testing instance creation:")
    business = Business.objects.create(name="Test Business")
    print(f"  ✅ Created Business: {business}")
    
    extension = BusinessExtension.objects.create(name="Test Extension", description="Test Description")
    print(f"  ✅ Created BusinessExtension: {extension}")
    
    # Test that they share the same table
    print("\n📝 Testing table sharing:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%business%'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  Tables found: {tables}")
        
        # Should only have one table for Business
        business_tables = [t for t in tables if 'business' in t.lower()]
        assert len(business_tables) == 1, f"Should only have one Business table, found: {business_tables}"
        print(f"  ✅ Only one Business table found: {business_tables[0]}")
    
    print("\n🎉 STI Solution Test Passed!")

if __name__ == "__main__":
    test_sti_solution() 