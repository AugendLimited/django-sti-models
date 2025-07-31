#!/usr/bin/env python
"""
Test the exact user pattern that was failing in their Django project.
This replicates their AugendModel + Business + BusinessExtension pattern.
"""

import os
import sys
import django
from django.conf import settings

# Configure Django settings exactly like a real project
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

# Import after Django setup
from django.db import models, connection
from django_sti_models import TypedModel, TypeField


# Simulate the user's exact AugendModel pattern
class AugendModel(TypedModel):
    """
    User's base abstract model with TypeField inheritance.
    This mimics their augend.common.models.AugendModel pattern.
    """
    model_type = TypeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Business(AugendModel):
    """
    User's Business model - should become an STI base.
    This mimics their exact pattern from the migration.
    """
    name = models.CharField(max_length=255)
    
    class Meta:
        app_label = 'augend_businesses'
        verbose_name_plural = "Businesses"


class BusinessExtension(Business):
    """
    User's BusinessExtension - should become a proxy model.
    This should NOT create a separate table.
    """
    description = models.TextField(blank=True, default="")
    
    class Meta:
        app_label = 'augend_businesses'
        verbose_name_plural = "Business Extensions"


def test_user_pattern():
    """Test that matches the user's exact failing scenario."""
    print("🧪 Testing User's Exact Pattern")
    print("=" * 50)
    
    print("\n📝 Model Hierarchy:")
    print("  AugendModel (abstract) -> contains TypeField")
    print("  ├── Business (concrete) -> inherits TypeField")
    print("  └── BusinessExtension (concrete) -> should be proxy")
    
    # Check STI detection
    business_is_sti_base = getattr(Business._meta, 'is_sti_base', False)
    extension_is_proxy = getattr(BusinessExtension._meta, 'proxy', False)
    extension_is_sti_subclass = getattr(BusinessExtension._meta, 'is_sti_subclass', False)
    
    print(f"\n🏷️ STI Detection Results:")
    print(f"  Business is STI base: {'✅ YES' if business_is_sti_base else '❌ NO'}")
    print(f"  BusinessExtension is proxy: {'✅ YES' if extension_is_proxy else '❌ NO'}")
    print(f"  BusinessExtension is STI subclass: {'✅ YES' if extension_is_sti_subclass else '❌ NO'}")
    
    # Check table names
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    tables_match = business_table == extension_table
    
    print(f"\n📊 Database Table Analysis:")
    print(f"  Business table: {business_table}")
    print(f"  BusinessExtension table: {extension_table}")
    print(f"  Tables match (STI): {'✅ YES' if tables_match else '❌ NO'}")
    
    # Simulate Django migration generation
    print(f"\n🔍 Migration Analysis:")
    if extension_is_proxy:
        print("  ✅ BusinessExtension would be proxy model in migration")
        print("  ✅ No separate table would be created")
    else:
        print("  ❌ BusinessExtension would create separate table")
        print("  ❌ Migration would show OneToOneField pointer")
    
    # Test actual database operations
    print(f"\n🏗️ Database Operations Test:")
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Business)
        print("  ✅ Business table created successfully")
        
        # Create instances
        business = Business.objects.create(name="Acme Corp")
        extension = BusinessExtension.objects.create(name="Tech Inc", description="A tech company")
        
        print(f"  ✅ Business created: {business} (type: {business.model_type})")
        print(f"  ✅ Extension created: {extension} (type: {extension.model_type})")
        
        # Test STI querying behavior
        all_businesses = Business.objects.all()
        extensions_only = BusinessExtension.objects.all()
        
        print(f"\n🔍 STI Query Behavior:")
        print(f"  All businesses count: {all_businesses.count()}")
        print(f"  Extensions only count: {extensions_only.count()}")
        
        # Extension should appear in base model query for true STI
        extension_in_base_query = extension in all_businesses
        print(f"  Extension appears in base query: {'✅ YES' if extension_in_base_query else '❌ NO'}")
        
        # Overall success criteria
        success = (business_is_sti_base and extension_is_proxy and 
                  extension_is_sti_subclass and tables_match and 
                  extension_in_base_query)
        
        print(f"\n🏁 Final Result:")
        if success:
            print("  🎉 SUCCESS! User pattern works with STI")
            print("  ✅ BusinessExtension will be a proxy model")
            print("  ✅ No separate table will be created in migration")
        else:
            print("  ❌ FAILED! STI not working properly")
            print("  ❌ BusinessExtension will create separate table")
            
        return success
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_user_pattern()
    if success:
        print("\n🚀 The user's pattern should now work!")
        print("   Delete existing migrations and run makemigrations again.")
    else:
        print("\n💔 The user's pattern still needs fixing.")
    
    sys.exit(0 if success else 1)