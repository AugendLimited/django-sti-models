#!/usr/bin/env python
"""
Debug and fix the Django app loading issue with STI.
"""

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

from django.db import models
from django_sti_models.models import TypedModelMeta
from django_sti_models import TypedModel, TypeField

print("🔍 Debugging Django App Loading Issue")
print("=" * 60)

# Let's trace exactly what happens during model creation
original_new = TypedModelMeta.__new__

def debug_metaclass(mcs, name, bases, namespace, **kwargs):
    print(f"\n🔧 Creating model: {name}")
    print(f"   Bases: {[b.__name__ for b in bases]}")
    
    # Check for TypeField in namespace
    typefield_in_namespace = any(isinstance(v, TypeField) for v in namespace.values())
    print(f"   TypeField in namespace: {typefield_in_namespace}")
    
    # Check for TypeField in bases (our inheritance fix)
    typefield_in_inheritance = mcs._has_typefield_in_bases(bases)
    print(f"   TypeField in inheritance: {typefield_in_inheritance}")
    
    # Check Meta settings
    Meta = namespace.get('Meta')
    if Meta:
        abstract = getattr(Meta, 'abstract', False)
        print(f"   Meta.abstract: {abstract}")
        if abstract:
            print(f"   ✅ Skipping abstract model")
            result = original_new(mcs, name, bases, namespace, **kwargs)
            return result
    
    # Check if this should be an STI base
    if typefield_in_namespace or typefield_in_inheritance:
        print(f"   ✅ Should be STI base (has TypeField)")
    
    # Check for typed base (for subclasses)
    typed_base = mcs._find_typed_base(bases)
    if typed_base:
        print(f"   ✅ Found typed base: {typed_base.__name__}")
        print(f"   ✅ This should be STI subclass (proxy)")
    
    # Call original and check result
    result = original_new(mcs, name, bases, namespace, **kwargs)
    
    # Check what was actually set
    if hasattr(result._meta, 'is_sti_base'):
        print(f"   Result is_sti_base: {result._meta.is_sti_base}")
    if hasattr(result._meta, 'proxy'):
        print(f"   Result proxy: {result._meta.proxy}")
    if hasattr(result._meta, 'is_sti_subclass'):
        print(f"   Result is_sti_subclass: {result._meta.is_sti_subclass}")
    
    print(f"   Final table: {result._meta.db_table}")
    
    return result

# Patch the metaclass for debugging
TypedModelMeta.__new__ = debug_metaclass

# Test model creation
print("🧪 Creating models with detailed tracing...")

class HookModelMixin(models.Model):
    class Meta:
        abstract = True

class CurrentUserField(models.ForeignKey):
    def __init__(self, related_name=None, on_update=None, **kwargs):
        kwargs.setdefault('to', 'auth.User')
        kwargs.setdefault('null', True)
        kwargs.setdefault('on_delete', models.CASCADE)
        super().__init__(**kwargs)

class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = CurrentUserField(related_name="created_%(class)ss", on_update=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = CurrentUserField(related_name="updated_%(class)ss", on_update=True)

    class Meta:
        abstract = True

class CloneMixin(models.Model):
    class Meta:
        abstract = True

print("\n" + "="*60)
print("Creating AugendModel...")

class AugendModel(TypedModel, AuditableModel, CloneMixin, HookModelMixin):
    model_type = TypeField()
    class Meta:
        abstract = True

print("\n" + "="*60)
print("Creating Business...")

class Business(AugendModel):
    name = models.CharField(max_length=255)
    class Meta:
        app_label = 'test'

print("\n" + "="*60)
print("Creating BusinessExtension...")

class BusinessExtension(Business):
    description = models.TextField(blank=True, default="")
    class Meta:
        app_label = 'test'

print(f"\n📋 Final Results:")
print(f"  Business is STI base: {getattr(Business._meta, 'is_sti_base', False)}")
print(f"  BusinessExtension is proxy: {getattr(BusinessExtension._meta, 'proxy', False)}")
print(f"  Same table: {Business._meta.db_table == BusinessExtension._meta.db_table}")