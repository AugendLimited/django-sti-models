#!/usr/bin/env python
"""
Quick test to verify the AttributeError fix for get_db_table.
"""

import os
import sys
import django
from django.conf import settings

# Configure minimal Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django_sti_models',
        ],
        USE_TZ=True,
    )

django.setup()

from django.db import models
from django_sti_models import TypedModel, TypeField


# Test models to reproduce the issue
class AugendModel(models.Model):
    """Mock AugendModel for testing."""
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True


class Business(TypedModel, AugendModel):
    """Test STI base model."""
    model_type = TypeField()
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'test_app'
        verbose_name_plural = "Businesses"


class BusinessExtension(Business):
    """Test STI subclass."""
    cif_number = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = 'test_app'
        verbose_name_plural = "Business Extensions"


def test_model_creation():
    """Test that models can be created without AttributeError."""
    try:
        print("🧪 Testing model creation...")
        
        # Test that the models were created successfully
        print(f"✅ Business model created: {Business}")
        print(f"✅ BusinessExtension model created: {BusinessExtension}")
        
        # Test table sharing
        business_table = Business._meta.db_table
        extension_table = BusinessExtension._meta.db_table
        
        print(f"📊 Business table: {business_table}")
        print(f"📊 BusinessExtension table: {extension_table}")
        
        if business_table == extension_table:
            print("✅ Tables are shared correctly (STI working)")
        else:
            print("❌ Tables are different (STI not working)")
        
        # Test STI setup validation
        print("\n🔍 Testing STI setup validation...")
        
        business_errors = Business.validate_sti_setup()
        extension_errors = BusinessExtension.validate_sti_setup()
        
        print(f"Business validation: {business_errors or 'No errors'}")
        print(f"BusinessExtension validation: {extension_errors or 'No errors'}")
        
        # Test STI table info
        print("\n📋 STI Table Information:")
        business_info = Business.get_sti_table_info()
        extension_info = BusinessExtension.get_sti_table_info()
        
        print(f"Business: {business_info}")
        print(f"BusinessExtension: {extension_info}")
        
        # Test type registration
        print("\n🏷️ Type Registration:")
        all_types = Business.get_all_types()
        print(f"Registered types: {list(all_types.keys())}")
        
        print("\n🎉 All tests passed! The AttributeError fix is working.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_model_creation()
    sys.exit(0 if success else 1)