#!/usr/bin/env python
"""
Debug when and how the metaclass is being called during model creation.
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
from django_sti_models import TypedModel, TypeField

print("🔍 Debugging Metaclass Execution")
print("=" * 50)

# Add debug prints to understand what's happening
original_new = TypedModel.__class__.__new__

def debug_new(mcs, name, bases, namespace, **kwargs):
    print(f"\n🔧 TypedModelMeta.__new__ called for: {name}")
    print(f"   Bases: {[b.__name__ for b in bases]}")
    print(f"   Has TypeField in namespace: {any(isinstance(v, TypeField) for v in namespace.values())}")
    
    # Check Meta settings
    Meta = namespace.get('Meta')
    if Meta:
        abstract = getattr(Meta, 'abstract', False)
        print(f"   Meta.abstract: {abstract}")
    else:
        print(f"   No Meta class")
    
    # Call original method
    result = original_new(mcs, name, bases, namespace, **kwargs)
    
    # Check result
    if hasattr(result._meta, 'is_sti_base'):
        print(f"   ✅ Result is_sti_base: {result._meta.is_sti_base}")
    if hasattr(result._meta, 'proxy'):
        print(f"   ✅ Result proxy: {result._meta.proxy}")
    if hasattr(result._meta, 'is_sti_subclass'):
        print(f"   ✅ Result is_sti_subclass: {result._meta.is_sti_subclass}")
    
    return result

# Monkey patch for debugging
TypedModel.__class__.__new__ = debug_new

print("🧪 Creating models with debug output...")

# Mock dependencies
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

# Your exact models
class AugendModel(TypedModel, AuditableModel, CloneMixin, HookModelMixin):
    model_type = TypeField()

    class Meta:
        abstract = True

class Business(AugendModel):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'test'
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name

class BusinessExtension(Business):
    description = models.TextField(blank=True, default="")

    class Meta:
        app_label = 'test'
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return self.name

print(f"\n📋 Final Results:")
print(f"  Business._meta.is_sti_base: {getattr(Business._meta, 'is_sti_base', 'NOT SET')}")
print(f"  BusinessExtension._meta.proxy: {getattr(BusinessExtension._meta, 'proxy', 'NOT SET')}")
print(f"  BusinessExtension._meta.is_sti_subclass: {getattr(BusinessExtension._meta, 'is_sti_subclass', 'NOT SET')}")