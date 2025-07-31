#!/usr/bin/env python
"""
Debug script to test the exact user model pattern.
"""

import os
import django
from django.conf import settings

# Configure Django first
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'],
        USE_TZ=True,
    )
django.setup()

from django.db import models
from django_sti_models import TypedModel, TypeField

print("🔍 Testing User's Exact Model Pattern")
print("=" * 50)

# Replicate the user's exact pattern
class AugendModel(TypedModel):
    """Exact replica of user's AugendModel."""
    model_type = TypeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

print("✅ AugendModel created (abstract)")

class Business(AugendModel):
    """Exact replica of user's Business model."""
    name = models.CharField(max_length=255)
    
    class Meta:
        app_label = 'augend_businesses'
        abstract = False
        verbose_name_plural = "Businesses"

print("✅ Business created (concrete)")

class BusinessExtension(Business):
    """Exact replica of user's BusinessExtension model."""
    description = models.TextField(blank=True, default="")
    
    class Meta:
        app_label = 'augend_businesses'
        verbose_name_plural = "Business Extensions"

print("✅ BusinessExtension created (should be proxy)")

# Debug the model creation process
print(f"\n🔍 Model Analysis:")
print(f"  Business._meta.abstract: {getattr(Business._meta, 'abstract', False)}")
print(f"  Business._meta.is_sti_base: {getattr(Business._meta, 'is_sti_base', False)}")
print(f"  BusinessExtension._meta.proxy: {getattr(BusinessExtension._meta, 'proxy', False)}")
print(f"  BusinessExtension._meta.is_sti_subclass: {getattr(BusinessExtension._meta, 'is_sti_subclass', False)}")

# Check table names
business_table = Business._meta.db_table
extension_table = BusinessExtension._meta.db_table
print(f"\n📊 Table Names:")
print(f"  Business: {business_table}")
print(f"  BusinessExtension: {extension_table}")
print(f"  Same table: {'✅ YES' if business_table == extension_table else '❌ NO'}")

# Check if the inheritance chain is working
print(f"\n🧬 Inheritance Analysis:")
print(f"  Business bases: {[b.__name__ for b in Business.__bases__]}")
print(f"  BusinessExtension bases: {[b.__name__ for b in BusinessExtension.__bases__]}")

# Test the metaclass detection manually
from django_sti_models.models import TypedModelMeta
print(f"\n🔧 Metaclass Detection Test:")
print(f"  Business has TypeField directly: {TypedModelMeta._has_type_field(Business)}")
print(f"  Business has TypeField in bases: {TypedModelMeta._has_typefield_in_bases(Business.__bases__)}")

# Check if BusinessExtension sees Business as typed base
print(f"  BusinessExtension typed base: {TypedModelMeta._find_typed_base(BusinessExtension.__bases__)}")

# Final assessment
is_working = (
    getattr(Business._meta, 'is_sti_base', False) and
    getattr(BusinessExtension._meta, 'proxy', False) and
    business_table == extension_table
)

print(f"\n🏁 Result:")
if is_working:
    print("  🎉 SUCCESS! Your pattern should work correctly")
    print("  ✅ BusinessExtension is a proxy model")
    print("  ✅ Migration should NOT create separate table")
else:
    print("  ❌ PROBLEM! Your pattern is not working")
    print("  ❌ BusinessExtension will create separate table")
    
    # Try to identify the issue
    if not getattr(Business._meta, 'is_sti_base', False):
        print("  🔍 Issue: Business not detected as STI base")
    if not getattr(BusinessExtension._meta, 'proxy', False):
        print("  🔍 Issue: BusinessExtension not set as proxy")

print(f"\n💡 If this shows SUCCESS but your migration still fails:")
print(f"   1. Make sure your project uses the SAME django-sti-models installation")
print(f"   2. Try: pip uninstall django-sti-models && pip install /path/to/this/package")
print(f"   3. Clear Python cache: python -Bc 'import py_compile; py_compile.compile(...)'")
print(f"   4. Restart your Django development server")