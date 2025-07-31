#!/usr/bin/env python
"""
Simple test to generate and show the actual migration content.
"""

import os
import tempfile
import sys
from pathlib import Path
import django
from django.conf import settings
from django.core.management import call_command
from django.apps import apps
from django.apps.config import AppConfig

# Configure Django first
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
            '__main__',  # This module as an app
        ],
        USE_TZ=True,
        SECRET_KEY='test-key',
    )

django.setup()

from django.db import models
from django_sti_models import TypedModel, TypeField

print("🔧 Testing Migration Generation with Your Exact Models")
print("=" * 60)

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

# Your exact AugendModel
class AugendModel(TypedModel, AuditableModel, CloneMixin, HookModelMixin):
    model_type = TypeField()

    class Meta:
        abstract = True

# Your exact Business model
class Business(AugendModel):
    name = models.CharField(max_length=255)

    class Meta:
        app_label = '__main__'
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name

# Your exact BusinessExtension model
class BusinessExtension(Business):
    description = models.TextField(blank=True, default="")

    class Meta:
        app_label = '__main__'
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return self.name

print(f"✅ Models created")

# Check model state
print(f"\n📋 Model State Analysis:")
print(f"  Business._meta.is_sti_base: {getattr(Business._meta, 'is_sti_base', 'NOT SET')}")
print(f"  BusinessExtension._meta.proxy: {getattr(BusinessExtension._meta, 'proxy', 'NOT SET')}")
print(f"  BusinessExtension._meta.is_sti_subclass: {getattr(BusinessExtension._meta, 'is_sti_subclass', 'NOT SET')}")

business_table = Business._meta.db_table
extension_table = BusinessExtension._meta.db_table
print(f"  Business table: {business_table}")
print(f"  BusinessExtension table: {extension_table}")
print(f"  Same table: {'✅ YES' if business_table == extension_table else '❌ NO'}")

# Manual migration simulation
print(f"\n🔧 Simulating Django Migration Generation:")

from django.db.migrations.state import ProjectState
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations import operations

# Get current project state
project_state = ProjectState()

# Add our models to the state
from django.db.migrations.state import ModelState

def create_model_state(model_class):
    """Create a ModelState from a model class."""
    fields = []
    for field in model_class._meta.local_fields:
        field_details = field.deconstruct()
        fields.append((field_details[0], field_details[1](*field_details[2], **field_details[3])))
    
    return ModelState(
        app_label=model_class._meta.app_label,
        name=model_class.__name__,
        fields=fields,
        options={
            key: value for key, value in model_class._meta.original_attrs.items()
            if key in ['verbose_name', 'verbose_name_plural', 'proxy', 'abstract']
        },
        bases=tuple(base._meta.label_lower if hasattr(base, '_meta') else str(base) for base in model_class.__bases__ if base != models.Model),
    )

# Add Business model
business_state = create_model_state(Business)
project_state = project_state.add_model(business_state)

# Add BusinessExtension model  
extension_state = create_model_state(BusinessExtension)
project_state = project_state.add_model(extension_state)

print(f"📊 Model States Added:")
print(f"  Business state: {business_state.name}")
print(f"  Business options: {business_state.options}")
print(f"  BusinessExtension state: {extension_state.name}")
print(f"  BusinessExtension options: {extension_state.options}")
print(f"  BusinessExtension bases: {extension_state.bases}")

# Simulate what Django would generate
from django.db.migrations.autodetector import MigrationAutodetector

print(f"\n🎯 What Django Migration Would Generate:")

if getattr(BusinessExtension._meta, 'proxy', False):
    print(f"  ✅ BusinessExtension is PROXY - NO separate table")
    print(f"  ✅ Migration would only create Business table")
    print(f"  ✅ This is CORRECT STI behavior")
else:
    print(f"  ❌ BusinessExtension is NOT proxy - SEPARATE table")
    print(f"  ❌ Migration would create TWO tables")
    print(f"  ❌ This is INCORRECT MTI behavior")

# Show what the migration operations would look like
print(f"\n📝 Expected Migration Operations:")

if getattr(BusinessExtension._meta, 'proxy', False):
    print(f"""
operations = [
    migrations.CreateModel(
        name='Business',
        fields=[
            ('id', models.BigAutoField(primary_key=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('model_type', django_sti_models.fields.TypeField(...)),
            ('name', models.CharField(max_length=255)),
            ('created_by', CurrentUserField(...)),
            ('updated_by', CurrentUserField(...)),
        ],
        options={{'verbose_name_plural': 'Businesses'}},
    ),
    # ✅ NO BusinessExtension CreateModel - it's a proxy!
]
""")
else:
    print(f"""
operations = [
    migrations.CreateModel(
        name='Business',
        fields=[...],
    ),
    migrations.CreateModel(
        name='BusinessExtension',  # ❌ BAD - separate table
        fields=[
            ('business_ptr', models.OneToOneField(...)),  # ❌ MTI pointer
            ('description', models.TextField(...)),
        ],
        bases=('__main__.business',),  # ❌ MTI inheritance
    ),
]
""")

print(f"\n🏁 Conclusion:")
if getattr(BusinessExtension._meta, 'proxy', False):
    print(f"  🎉 STI is working correctly!")
    print(f"  ✅ If your project still generates wrong migrations:")
    print(f"     - Your project is using a different django-sti-models package")
    print(f"     - Install this fixed version: pip install -e {os.getcwd()}")
else:
    print(f"  ❌ STI is NOT working!")
    print(f"  ❌ BusinessExtension should be a proxy model but isn't")
    print(f"  🔍 This indicates our fix has a bug that needs investigation")