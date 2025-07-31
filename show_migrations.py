#!/usr/bin/env python
"""
Generate actual Django migrations to show what's being created.
"""

import os
import tempfile
import shutil
from pathlib import Path
import django
from django.conf import settings
from django.core.management import call_command
from django.core.management.commands.makemigrations import Command as MakeMigrationsCommand
from io import StringIO
import sys

# Create a test app directory structure
temp_dir = Path(tempfile.mkdtemp())
app_dir = temp_dir / 'test_businesses'
migrations_dir = app_dir / 'migrations'

# Create directories
app_dir.mkdir()
migrations_dir.mkdir()

# Create __init__.py files
(app_dir / '__init__.py').write_text('')
(migrations_dir / '__init__.py').write_text('')

# Create models.py with your exact pattern
models_content = '''
from django.db import models
from django.forms.models import model_to_dict
from django_sti_models import TypedModel, TypeField

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

    def clone(self, exclude_fields=None, override_fields=None):
        exclude_fields = set(exclude_fields or [])
        override_fields = override_fields or {}
        field_values = {}
        field_values.update(override_fields)
        return self.__class__(**field_values)

# Your exact AugendModel
class AugendModel(TypedModel, AuditableModel, CloneMixin, HookModelMixin):
    model_type = TypeField()

    class Meta:
        abstract = True

# Your exact Business model
class Business(AugendModel):
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name

# Your exact BusinessExtension model
class BusinessExtension(Business):
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return self.name
'''

(app_dir / 'models.py').write_text(models_content)

# Create apps.py
apps_content = '''
from django.apps import AppConfig

class TestBusinessesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'test_businesses'
'''

(app_dir / 'apps.py').write_text(apps_content)

# Add to Python path
sys.path.insert(0, str(temp_dir))

try:
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
                'test_businesses',
            ],
            USE_TZ=True,
        )

    django.setup()

    print("🏗️ Generating Django Migrations for Your Models")
    print("=" * 60)

    # First, let's check the model state
    from test_businesses.models import Business, BusinessExtension
    
    print(f"\n📋 Model Analysis:")
    print(f"  Business._meta.is_sti_base: {getattr(Business._meta, 'is_sti_base', False)}")
    print(f"  BusinessExtension._meta.proxy: {getattr(BusinessExtension._meta, 'proxy', False)}")
    print(f"  BusinessExtension._meta.is_sti_subclass: {getattr(BusinessExtension._meta, 'is_sti_subclass', False)}")
    
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    print(f"  Business table: {business_table}")
    print(f"  BusinessExtension table: {extension_table}")
    print(f"  Same table: {'✅ YES' if business_table == extension_table else '❌ NO'}")

    # Generate migrations
    print(f"\n🔧 Generating migrations...")
    
    # Capture output
    out = StringIO()
    call_command(
        'makemigrations', 
        'test_businesses',
        verbosity=2,
        interactive=False,
        stdout=out
    )
    
    print(out.getvalue())

    # Find and read the generated migration
    migration_files = list(migrations_dir.glob('*.py'))
    migration_files = [f for f in migration_files if f.name != '__init__.py']
    
    if migration_files:
        migration_file = migration_files[0]
        print(f"\n📄 Generated Migration ({migration_file.name}):")
        print("=" * 60)
        
        with open(migration_file, 'r') as f:
            migration_content = f.read()
            print(migration_content)
        
        print("\n" + "=" * 60)
        
        # Analyze the migration
        print(f"\n🔍 Migration Analysis:")
        
        creates_business = 'Business' in migration_content and 'CreateModel' in migration_content
        creates_extension = 'BusinessExtension' in migration_content and 'CreateModel' in migration_content
        has_proxy = 'proxy' in migration_content.lower()
        has_onetoone = 'OneToOneField' in migration_content
        
        print(f"  Creates Business table: {'✅ YES' if creates_business else '❌ NO'}")
        print(f"  Creates BusinessExtension table: {'❌ BAD' if creates_extension else '✅ GOOD'}")
        print(f"  Has proxy reference: {'✅ YES' if has_proxy else '❌ NO'}")
        print(f"  Has OneToOneField (MTI): {'❌ BAD' if has_onetoone else '✅ GOOD'}")
        
        if creates_business and not creates_extension and not has_onetoone:
            print(f"\n🎉 SUCCESS! Migration correctly implements STI")
            print(f"   ✅ Only Business table is created")
            print(f"   ✅ BusinessExtension is a proxy model")
        else:
            print(f"\n❌ PROBLEM! Migration shows MTI, not STI")
            print(f"   ❌ BusinessExtension will have separate table")
            if has_onetoone:
                print(f"   ❌ OneToOneField indicates Multi-Table Inheritance")
    else:
        print("❌ No migration file was generated!")

finally:
    # Cleanup
    if str(temp_dir) in sys.path:
        sys.path.remove(str(temp_dir))
    shutil.rmtree(temp_dir)