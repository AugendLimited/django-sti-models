#!/usr/bin/env python
"""
Simple test to verify STI is working in your Django environment.
Run this in your Django project to confirm the fix.
"""
import os
import django

# Configure Django (adjust the settings module to match your project)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

# Import your STI models
from corrected_business_models import Business, BusinessExtension

def test_sti_proxy_models():
    """Test that our STI fix is working correctly."""
    print("🧪 Testing STI Proxy Model Implementation")
    print("=" * 50)
    
    # Test 1: Check proxy settings
    print("1. Checking proxy model settings:")
    business_proxy = getattr(Business._meta, 'proxy', False)
    extension_proxy = getattr(BusinessExtension._meta, 'proxy', False)
    
    print(f"   Business._meta.proxy: {business_proxy}")
    print(f"   BusinessExtension._meta.proxy: {extension_proxy}")
    
    # Test 2: Check table sharing
    print("\n2. Checking table sharing:")
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    
    print(f"   Business table: {business_table}")
    print(f"   BusinessExtension table: {extension_table}")
    print(f"   Tables match: {business_table == extension_table}")
    
    # Test 3: Verify STI behavior
    print("\n3. Results:")
    if not business_proxy and extension_proxy and business_table == extension_table:
        print("   ✅ SUCCESS: STI is working correctly!")
        print("   ✅ Base model is concrete, subclass is proxy")
        print("   ✅ Both models share the same database table")
        print("   ✅ Django migrations will create only ONE table")
        return True
    else:
        print("   ❌ FAILURE: STI configuration is incorrect")
        if business_proxy:
            print("   ❌ Base model should not be proxy")
        if not extension_proxy:
            print("   ❌ Subclass should be proxy")
        if business_table != extension_table:
            print("   ❌ Models should share the same table")
        return False

if __name__ == "__main__":
    success = test_sti_proxy_models()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 STI FIX IS WORKING!")
        print("✅ Your Django migrations should now work correctly")
        print("✅ Only one database table will be created")
    else:
        print("❌ STI fix needs debugging")
    
    exit(0 if success else 1)