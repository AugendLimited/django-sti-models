#!/usr/bin/env python
"""
Run this in your ACTUAL Django project to verify the package version.
"""

print("🔍 Verifying django-sti-models in your project")
print("=" * 50)

try:
    # Check package location and version
    import django_sti_models
    print(f"✅ Package location: {django_sti_models.__file__}")
    
    # Check if our fix is present
    from django_sti_models.models import TypedModelMeta
    has_fix = hasattr(TypedModelMeta, '_has_typefield_in_bases')
    print(f"🔧 Has inheritance fix: {'✅ YES' if has_fix else '❌ NO'}")
    
    if not has_fix:
        print("❌ PROBLEM: Your project is using an OLD version!")
        print("   Solution: pip install -e /path/to/fixed/django-sti-models")
        exit(1)
    
    # Test with your actual models (adjust import path)
    print("\n🧪 Testing your actual models...")
    
    # Import your actual AugendModel and Business models
    # CHANGE THESE IMPORTS to match your project:
    from augend.common.models import AugendModel
    from augend_businesses.models import Business, BusinessExtension
    
    # Check STI status
    business_sti = getattr(Business._meta, 'is_sti_base', False)
    extension_proxy = getattr(BusinessExtension._meta, 'proxy', False)
    
    print(f"📋 Your actual models:")
    print(f"  Business is STI base: {'✅ YES' if business_sti else '❌ NO'}")
    print(f"  BusinessExtension is proxy: {'✅ YES' if extension_proxy else '❌ NO'}")
    
    if business_sti and extension_proxy:
        print("\n🎉 SUCCESS! Your models should work correctly")
        print("   If migration still fails, try:")
        print("   1. Delete existing migrations")
        print("   2. Restart Django server")  
        print("   3. python manage.py makemigrations --empty your_app")
        print("   4. python manage.py makemigrations")
    else:
        print("\n❌ PROBLEM! STI not working in your project")
        print("   Debug: Check model loading order and imports")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Make sure to run this in your Django project directory")
    print("   And adjust the import paths to match your project")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()