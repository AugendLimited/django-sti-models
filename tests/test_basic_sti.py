#!/usr/bin/env python
"""
Very basic test of STI functionality without Django apps complexity.
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
    )

django.setup()

# Import after Django setup
from django.db import models, connection
from django_sti_models import TypedModel, TypeField


class Business(TypedModel):
    """Simple STI base model."""
    model_type = TypeField()
    name = models.CharField(max_length=255)
    
    class Meta:
        app_label = 'test'


class BusinessExtension(Business):
    """STI subclass."""
    cif_number = models.CharField(max_length=255, blank=True)
    
    class Meta:
        app_label = 'test'


def test_basic_sti():
    """Test basic STI functionality."""
    print("🧪 Testing Basic STI Functionality\n")
    
    # Check table names
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    
    print(f"📊 Table Names:")
    print(f"  Business: {business_table}")
    print(f"  BusinessExtension: {extension_table}")
    
    tables_match = business_table == extension_table
    print(f"  Tables match: {'✅ Yes' if tables_match else '❌ No'}")
    
    # Check STI flags
    is_base = getattr(Business._meta, 'is_sti_base', False)
    is_subclass = getattr(BusinessExtension._meta, 'is_sti_subclass', False)
    
    print(f"\n🏷️ STI Flags:")
    print(f"  Business is STI base: {'✅ Yes' if is_base else '❌ No'}")
    print(f"  BusinessExtension is STI subclass: {'✅ Yes' if is_subclass else '❌ No'}")
    
    # Check type field names
    business_type_field = Business.get_type_field_name()
    extension_type_field = BusinessExtension.get_type_field_name()
    
    print(f"\n📝 Type Field Names:")
    print(f"  Business: {business_type_field}")
    print(f"  BusinessExtension: {extension_type_field}")
    
    # Check type registration
    business_types = Business.get_all_types()
    
    print(f"\n📋 Type Registration:")
    print(f"  Business types: {list(business_types.keys())}")
    
    # Create table and test instances
    print(f"\n🏗️ Creating Table and Testing Instances:")
    
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Business)
        print("  ✅ Table created")
        
        # Test instance creation
        business = Business.objects.create(name="Acme Corp")
        extension = BusinessExtension.objects.create(name="Tech Inc", cif_number="B123")
        
        print(f"  ✅ Business created: {business} (type: {business.model_type})")
        print(f"  ✅ Extension created: {extension} (type: {extension.model_type})")
        
        # Test querying
        all_businesses = Business.objects.all()
        extensions_only = BusinessExtension.objects.all()
        
        print(f"\n🔍 Query Results:")
        print(f"  All businesses: {all_businesses.count()}")
        print(f"  Extensions only: {extensions_only.count()}")
        
        success = (tables_match and is_base and is_subclass and 
                  all_businesses.count() == 2 and extensions_only.count() == 1)
        
        print(f"\n🏁 Overall Result: {'🎉 Success!' if success else '❌ Failed'}")
        return success
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_basic_sti()
    sys.exit(0 if success else 1)