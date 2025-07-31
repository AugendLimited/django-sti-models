#!/usr/bin/env python
"""
Check what version of django-sti-models is being used and test the fix.
"""

import sys
import importlib

print("🔍 Package Version Check")
print("=" * 40)

try:
    # Configure Django first
    import os
    import django
    from django.conf import settings
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
            INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'],
            USE_TZ=True,
        )
    django.setup()
    
    # Now import django-sti-models
    import django_sti_models
    print(f"✅ django-sti-models imported successfully")
    print(f"📍 Location: {django_sti_models.__file__}")
    
    # Check if our fix is present
    from django_sti_models.models import TypedModelMeta
    
    # Test if our new method exists
    has_inheritance_method = hasattr(TypedModelMeta, '_has_typefield_in_bases')
    print(f"🔧 Has inheritance fix: {'✅ YES' if has_inheritance_method else '❌ NO'}")
    
    if has_inheritance_method:
        print("✅ The package has been updated with the inheritance fix!")
    else:
        print("❌ The package does NOT have the inheritance fix!")
        print("   You need to reinstall the updated package.")
    
    # Test with a simple example
    print(f"\n🧪 Testing TypeField inheritance detection:")
    
    from django.db import models
    from django_sti_models import TypedModel, TypeField
    
    class TestAbstract(TypedModel):
        model_type = TypeField()
        class Meta:
            abstract = True
    
    class TestConcrete(TestAbstract):
        name = models.CharField(max_length=100)
        class Meta:
            app_label = 'test'
    
    # Test inheritance detection
    meta = TypedModelMeta()
    has_typefield_in_bases = meta._has_typefield_in_bases(TestConcrete.__bases__)
    is_sti_base = getattr(TestConcrete._meta, 'is_sti_base', False)
    
    print(f"  Inheritance detection works: {'✅ YES' if has_typefield_in_bases else '❌ NO'}")
    print(f"  Concrete model is STI base: {'✅ YES' if is_sti_base else '❌ NO'}")
    
    if has_inheritance_method and has_typefield_in_bases and is_sti_base:
        print(f"\n🎉 SUCCESS! The fix is working in this environment.")
        print(f"   Your project should use this same package installation.")
    else:
        print(f"\n❌ PROBLEM! The fix is not working properly.")
        print(f"   Check if your project is using a different django-sti-models installation.")
        
except ImportError as e:
    print(f"❌ Failed to import django-sti-models: {e}")
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()

print(f"\n📋 Python Path:")
for i, path in enumerate(sys.path[:5]):  # Show first 5 paths
    print(f"  {i+1}. {path}")
print("...")