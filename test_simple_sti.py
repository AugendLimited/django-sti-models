#!/usr/bin/env python
"""
Simple test to verify the cleaned up STI framework works.
"""

import os
import sys
import django
from django.conf import settings

# Configure Django
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
        ],
        USE_TZ=True,
    )

django.setup()

from django.db import connection
from examples.business_models import Business, BusinessExtension, PremiumBusiness


def test_simple_sti():
    """Test the simplified STI implementation."""
    print("🚀 Testing Simplified STI Framework\n")
    
    # Create the table
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(Business)
    
    print("✅ Created database table")
    
    # Test table sharing
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    premium_table = PremiumBusiness._meta.db_table
    
    print(f"📊 Table Names:")
    print(f"  Business: {business_table}")
    print(f"  BusinessExtension: {extension_table}")
    print(f"  PremiumBusiness: {premium_table}")
    
    tables_match = business_table == extension_table == premium_table
    print(f"  Table sharing: {'✅ Working' if tables_match else '❌ Failed'}")
    
    # Test type field names
    business_type_field = Business.get_type_field_name()
    extension_type_field = BusinessExtension.get_type_field_name()
    
    print(f"📝 Type Field Names:")
    print(f"  Business: {business_type_field}")
    print(f"  BusinessExtension: {extension_type_field}")
    
    # Test instance creation
    print(f"\n🏗️ Creating Instances:")
    
    try:
        business = Business.objects.create(name="Acme Corp")
        print(f"  ✅ Business: {business} (type: {business.model_type})")
        
        extension = BusinessExtension.objects.create(name="Tech Inc", cif_number="B123")
        print(f"  ✅ BusinessExtension: {extension} (type: {extension.model_type})")
        
        premium = PremiumBusiness.objects.create(name="Elite Corp", premium_level="platinum")
        print(f"  ✅ PremiumBusiness: {premium} (type: {premium.model_type})")
        
    except Exception as e:
        print(f"  ❌ Instance creation failed: {e}")
        return False
    
    # Test querying
    print(f"\n🔍 Testing Queries:")
    
    try:
        all_businesses = Business.objects.all()
        extensions_only = BusinessExtension.objects.all()
        premium_only = PremiumBusiness.objects.all()
        
        print(f"  All businesses: {all_businesses.count()} (should be 3)")
        print(f"  Extensions only: {extensions_only.count()} (should be 1)")
        print(f"  Premium only: {premium_only.count()} (should be 1)")
        
        query_success = (all_businesses.count() == 3 and 
                        extensions_only.count() == 1 and
                        premium_only.count() == 1)
        
        print(f"  Query filtering: {'✅ Working' if query_success else '❌ Failed'}")
        
    except Exception as e:
        print(f"  ❌ Querying failed: {e}")
        return False
    
    # Test type registration
    print(f"\n📋 Type Registration:")
    try:
        all_types = Business.get_all_types()
        print(f"  Registered types: {list(all_types.keys())}")
        
        type_registration_success = (
            'Business' in all_types and
            'BusinessExtension' in all_types and
            'PremiumBusiness' in all_types
        )
        
        print(f"  Type registration: {'✅ Working' if type_registration_success else '❌ Failed'}")
        
    except Exception as e:
        print(f"  ❌ Type registration failed: {e}")
        return False
    
    # Final result
    all_tests_passed = tables_match and query_success and type_registration_success
    
    print(f"\n🏁 Test Results: {'🎉 All tests passed!' if all_tests_passed else '❌ Some tests failed'}")
    
    return all_tests_passed


if __name__ == "__main__":
    success = test_simple_sti()
    sys.exit(0 if success else 1)