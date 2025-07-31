#!/usr/bin/env python
"""
Test the STI solution with the user's exact model structure using ContentType.
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
        INSTALLED_APPS=['django_sti_models', 'django.contrib.contenttypes'],
    )

django.setup()

# Import after Django setup
from django.db import models, connection
from django_sti_models import TypedModel

# Mock the AugendModel and other dependencies
class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

# Your exact AugendModel - NO model_type field needed!
class AugendModel(TypedModel):
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
    print("🧪 Testing STI Solution with ContentType Approach\n")
    
    # Check that Business is set up as STI model
    print("📝 Checking Business model:")
    assert hasattr(Business._meta, 'is_sti_model'), "Business should be marked as STI model"
    assert Business._meta.is_sti_model, "Business should be marked as STI model"
    print("  ✅ Business is marked as STI model")
    
    # Check that BusinessExtension is also set up as STI model
    print("\n📝 Checking BusinessExtension model:")
    assert hasattr(BusinessExtension._meta, 'is_sti_model'), "BusinessExtension should be marked as STI model"
    assert BusinessExtension._meta.is_sti_model, "BusinessExtension should be marked as STI model"
    print("  ✅ BusinessExtension is marked as STI model")
    
    # Test creating instances
    print("\n📝 Testing instance creation:")
    business = Business.objects.create(name="Test Business")
    print(f"  ✅ Created Business: {business}")
    print(f"  ✅ Business polymorphic_ctype: {business.polymorphic_ctype}")
    
    extension = BusinessExtension.objects.create(name="Test Extension", description="Test Description")
    print(f"  ✅ Created BusinessExtension: {extension}")
    print(f"  ✅ Extension polymorphic_ctype: {extension.polymorphic_ctype}")
    
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
    
    # Test type-aware querying
    print("\n📝 Testing type-aware querying:")
    all_businesses = Business.objects.all()
    print(f"  ✅ All businesses: {list(all_businesses)}")
    
    all_extensions = BusinessExtension.objects.all()
    print(f"  ✅ All extensions: {list(all_extensions)}")
    
    # Test getting real instance class
    print("\n📝 Testing real instance class:")
    real_business_class = business.get_real_instance_class()
    print(f"  ✅ Business real class: {real_business_class}")
    assert real_business_class == Business, "Should return Business class"
    
    real_extension_class = extension.get_real_instance_class()
    print(f"  ✅ Extension real class: {real_extension_class}")
    assert real_extension_class == BusinessExtension, "Should return BusinessExtension class"
    
    print("\n🎉 STI Solution Test Passed!")

if __name__ == "__main__":
    test_sti_solution() 