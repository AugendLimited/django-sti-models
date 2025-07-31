#!/usr/bin/env python
"""
Test that actually generates Django migrations to verify STI behavior.
This should catch issues that the runtime tests miss.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import django
from django.conf import settings
from django.core.management import call_command
from django.apps import apps
from django.apps.config import AppConfig

# Configure Django for migration testing
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
            'test_app',  # Our test app
        ],
        USE_TZ=True,
    )

django.setup()

# Import after Django setup
from django.db import models
from django_sti_models import TypedModel, TypeField


# Define models in the test_app namespace
class TestAugendModel(TypedModel):
    """Test version of user's AugendModel."""
    model_type = TypeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'test_app'
        abstract = True


class TestBusiness(TestAugendModel):
    """Test version of user's Business model."""
    name = models.CharField(max_length=255)
    
    class Meta:
        app_label = 'test_app'
        verbose_name_plural = "Test Businesses"


class TestBusinessExtension(TestBusiness):
    """Test version of user's BusinessExtension."""
    description = models.TextField(blank=True, default="")
    
    class Meta:
        app_label = 'test_app'
        verbose_name_plural = "Test Business Extensions"


def test_migration_generation():
    """Test that migrations are generated correctly for STI models."""
    print("🧪 Testing Django Migration Generation")
    print("=" * 50)
    
    # Check STI setup first
    business_is_sti_base = getattr(TestBusiness._meta, 'is_sti_base', False)
    extension_is_proxy = getattr(TestBusinessExtension._meta, 'proxy', False)
    
    print(f"\n🏷️ Model Analysis:")
    print(f"  TestBusiness is STI base: {'✅ YES' if business_is_sti_base else '❌ NO'}")
    print(f"  TestBusinessExtension is proxy: {'✅ YES' if extension_is_proxy else '❌ NO'}")
    
    # Create temporary directory for migrations
    with tempfile.TemporaryDirectory() as temp_dir:
        migrations_dir = Path(temp_dir) / 'test_app' / 'migrations'
        migrations_dir.mkdir(parents=True)
        
        # Create __init__.py files
        (migrations_dir.parent / '__init__.py').touch()
        (migrations_dir / '__init__.py').touch()
        
        # Add the temp dir to Python path
        sys.path.insert(0, temp_dir)
        
        try:
            print(f"\n🏗️ Generating Migrations...")
            print(f"  Migrations directory: {migrations_dir}")
            
            # Generate migrations
            call_command(
                'makemigrations', 
                'test_app',
                verbosity=2,
                interactive=False,
                migration_name='initial'
            )
            
            # Find the generated migration file
            migration_files = list(migrations_dir.glob('*.py'))
            migration_files = [f for f in migration_files if f.name != '__init__.py']
            
            if migration_files:
                migration_file = migration_files[0]
                print(f"  ✅ Migration generated: {migration_file.name}")
                
                # Read and analyze the migration
                with open(migration_file, 'r') as f:
                    migration_content = f.read()
                
                print(f"\n📋 Migration Analysis:")
                
                # Check for separate BusinessExtension table creation
                has_business_table = 'TestBusiness' in migration_content
                has_extension_table = 'TestBusinessExtension' in migration_content
                has_proxy_reference = 'proxy' in migration_content.lower()
                has_onetoone_ptr = 'OneToOneField' in migration_content
                
                print(f"  Creates TestBusiness table: {'✅ YES' if has_business_table else '❌ NO'}")
                print(f"  Creates TestBusinessExtension table: {'❌ BAD' if has_extension_table else '✅ GOOD'}")
                print(f"  Has proxy reference: {'✅ YES' if has_proxy_reference else '❌ NO'}")
                print(f"  Has OneToOneField pointer: {'❌ BAD' if has_onetoone_ptr else '✅ GOOD'}")
                
                # Print relevant parts of the migration
                print(f"\n📄 Migration Content (relevant parts):")
                lines = migration_content.split('\n')
                for i, line in enumerate(lines):
                    if 'TestBusinessExtension' in line or 'OneToOneField' in line or 'proxy' in line.lower():
                        print(f"  Line {i+1}: {line.strip()}")
                
                # Determine success
                success = (business_is_sti_base and extension_is_proxy and 
                          has_business_table and not has_extension_table and 
                          not has_onetoone_ptr)
                
                print(f"\n🏁 Migration Test Result:")
                if success:
                    print("  🎉 SUCCESS! STI migrations work correctly")
                    print("  ✅ BusinessExtension will be a proxy model")
                else:
                    print("  ❌ FAILED! STI migrations not working")
                    print("  ❌ BusinessExtension creates separate table")
                    
                return success
                
            else:
                print("  ❌ No migration file generated")
                return False
                
        except Exception as e:
            print(f"  ❌ Migration generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Clean up sys.path
            if temp_dir in sys.path:
                sys.path.remove(temp_dir)


if __name__ == "__main__":
    success = test_migration_generation()
    sys.exit(0 if success else 1)