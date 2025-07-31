#!/usr/bin/env python
"""
Test the user's EXACT model definitions to see why STI isn't working.
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
from django.forms.models import model_to_dict
from django_sti_models import TypedModel, TypeField

print("🔍 Testing User's EXACT Model Definitions")
print("=" * 60)

# Mock the dependencies
class HookModelMixin(models.Model):
    class Meta:
        abstract = True

class CurrentUserField(models.ForeignKey):
    def __init__(self, related_name=None, on_update=None, **kwargs):
        kwargs.setdefault('to', 'auth.User')
        kwargs.setdefault('null', True)
        kwargs.setdefault('on_delete', models.CASCADE)
        super().__init__(**kwargs)

# User's exact AuditableModel
class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = CurrentUserField(related_name="created_%(class)ss", on_update=False)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = CurrentUserField(related_name="updated_%(class)ss", on_update=True)

    class Meta:
        abstract = True

# User's exact CloneMixin
class CloneMixin(models.Model):
    class Meta:
        abstract = True

    def clone(self, exclude_fields=None, override_fields=None):
        exclude_fields = set(exclude_fields or [])
        override_fields = override_fields or {}

        for field in self._meta.get_fields():
            if isinstance(field, models.Field):
                if field.auto_created or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                    exclude_fields.add(field.name)

        field_values = model_to_dict(self)

        for field in ["id", "pk", *list(exclude_fields)]:
            field_values.pop(field, None)

        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name in field_values:
                field_values[field.name] = getattr(self, field.name)

        field_values.update(override_fields)

        return self.__class__(**field_values)

# User's EXACT AugendModel
class AugendModel(TypedModel, AuditableModel, CloneMixin, HookModelMixin):
    model_type = TypeField()

    class Meta:
        abstract = True

print("✅ AugendModel created with user's exact definition")

# User's EXACT Business model  
class Business(AugendModel):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = 'augend_businesses'
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name

print("✅ Business created with user's exact definition")

# User's EXACT BusinessExtension model
class BusinessExtension(Business):
    description = models.TextField(blank=True, default="")

    class Meta:
        app_label = 'augend_businesses'
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return self.name

print("✅ BusinessExtension created with user's exact definition")

# Detailed analysis
print(f"\n🔍 Detailed Model Analysis:")

# Check AugendModel
print(f"\n📋 AugendModel:")
print(f"  Abstract: {getattr(AugendModel._meta, 'abstract', False)}")
print(f"  Has TypeField: {any(isinstance(f, TypeField) for f in AugendModel._meta.get_fields())}")

# Check Business  
print(f"\n📋 Business:")
print(f"  Abstract: {getattr(Business._meta, 'abstract', False)}")
print(f"  Is STI base: {getattr(Business._meta, 'is_sti_base', False)}")
print(f"  Has TypeField: {any(isinstance(f, TypeField) for f in Business._meta.get_fields())}")
print(f"  Bases: {[b.__name__ for b in Business.__bases__]}")

# Check BusinessExtension
print(f"\n📋 BusinessExtension:")
print(f"  Abstract: {getattr(BusinessExtension._meta, 'abstract', False)}")
print(f"  Is proxy: {getattr(BusinessExtension._meta, 'proxy', False)}")
print(f"  Is STI subclass: {getattr(BusinessExtension._meta, 'is_sti_subclass', False)}")
print(f"  Bases: {[b.__name__ for b in BusinessExtension.__bases__]}")

# Table analysis
business_table = Business._meta.db_table
extension_table = BusinessExtension._meta.db_table
print(f"\n📊 Table Analysis:")
print(f"  Business table: {business_table}")
print(f"  BusinessExtension table: {extension_table}")
print(f"  Same table: {'✅ YES' if business_table == extension_table else '❌ NO'}")

# Metaclass debugging
from django_sti_models.models import TypedModelMeta
print(f"\n🔧 Metaclass Analysis:")

# Check Business STI base detection
business_has_typefield_direct = TypedModelMeta._has_type_field(Business)
business_has_typefield_bases = TypedModelMeta._has_typefield_in_bases(Business.__bases__)
print(f"  Business has TypeField directly: {business_has_typefield_direct}")
print(f"  Business has TypeField in bases: {business_has_typefield_bases}")

# Check BusinessExtension typed base detection
extension_typed_base = TypedModelMeta._find_typed_base(BusinessExtension.__bases__)
print(f"  BusinessExtension typed base found: {extension_typed_base}")

# Final result
is_working = (
    getattr(Business._meta, 'is_sti_base', False) and
    getattr(BusinessExtension._meta, 'proxy', False) and
    business_table == extension_table
)

print(f"\n🏁 Final Assessment:")
if is_working:
    print("  🎉 SUCCESS! User's exact models work with STI")
    print("  ✅ This should NOT create separate tables in migration")
    print("  💡 If migration still creates separate tables, check:")
    print("     - Django is using the updated django-sti-models package")
    print("     - Clear Django's model cache/restart server")
    print("     - Check for any model loading order issues")
else:
    print("  ❌ PROBLEM! User's exact models are not working with STI")
    if not getattr(Business._meta, 'is_sti_base', False):
        print("     🔍 Business not detected as STI base")
    if not getattr(BusinessExtension._meta, 'proxy', False):
        print("     🔍 BusinessExtension not set as proxy")
    if business_table != extension_table:
        print("     🔍 Different table names indicate MTI, not STI")

# Debug the MRO (Method Resolution Order)
print(f"\n🧬 Method Resolution Order (MRO):")
print(f"  Business MRO: {[cls.__name__ for cls in Business.__mro__]}")
print(f"  BusinessExtension MRO: {[cls.__name__ for cls in BusinessExtension.__mro__]}")

# Check multiple inheritance order
print(f"\n🔀 Multiple Inheritance Analysis:")
print(f"  AugendModel bases: {[b.__name__ for b in AugendModel.__bases__]}")
print("  Order: TypedModel, AuditableModel, CloneMixin, HookModelMixin")
print("  TypedModel should be FIRST for metaclass to work properly")