#!/usr/bin/env python
"""
Generate the actual Django migration file to see what's being created.
"""

import os
import tempfile
import shutil
import sys
from pathlib import Path
import django
from django.conf import settings
from django.core.management import call_command
from django.apps import apps

# Create a complete test Django project structure
temp_dir = Path(tempfile.mkdtemp())
project_dir = temp_dir / 'testproject'
app_dir = project_dir / 'augend_businesses'
migrations_dir = app_dir / 'migrations'

print(f"🏗️ Creating test Django project in: {temp_dir}")

# Create directory structure
project_dir.mkdir()
app_dir.mkdir()
migrations_dir.mkdir()

# Create __init__.py files
(project_dir / '__init__.py').write_text('')
(app_dir / '__init__.py').write_text('')
(migrations_dir / '__init__.py').write_text('')

# Create Django settings.py
settings_content = '''
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'test-secret-key'
DEBUG = True

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'augend_businesses',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

USE_TZ = True
'''
(project_dir / 'settings.py').write_text(settings_content)

# Create app's apps.py
apps_content = '''
from django.apps import AppConfig

class AugendBusinessesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'augend_businesses'
'''
(app_dir / 'apps.py').write_text(apps_content)

# Create models.py with your EXACT model definitions
models_content = '''
from django.db import models
from django.forms.models import model_to_dict
from django_sti_models import TypedModel, TypeField

# Mock django_bulk_hooks and django_currentuser
class HookModelMixin(models.Model):
    class Meta:
        abstract = True

class CurrentUserField(models.ForeignKey):
    def __init__(self, related_name=None, on_update=None, **kwargs):
        kwargs.setdefault('to', 'auth.User')
        kwargs.setdefault('null', True)
        kwargs.setdefault('on_delete', models.CASCADE)
        kwargs.setdefault('default', lambda: None)
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

        for field in self._meta.get_fields():
            if isinstance(field, models.Field):
                if field.auto_created or getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                    exclude_fields.add(field.name)

        field_values = {}
        for field in ["id", "pk", *list(exclude_fields)]:
            field_values.pop(field, None)

        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name in field_values:
                field_values[field.name] = getattr(self, field.name)

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

# Create manage.py
manage_content = '''#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproject.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
'''
(project_dir / 'manage.py').write_text(manage_content)

# Add project to Python path
sys.path.insert(0, str(project_dir))
os.chdir(project_dir)

try:
    # Configure Django
    os.environ['DJANGO_SETTINGS_MODULE'] = 'testproject.settings'
    
    import testproject.settings
    if not settings.configured:
        settings.configure(**{key: getattr(testproject.settings, key) for key in dir(testproject.settings) if not key.startswith('_')})
    
    django.setup()

    print(f"✅ Django project set up successfully")
    
    # Import and check the models
    from augend_businesses.models import Business, BusinessExtension
    
    print(f"\n📋 Model Analysis:")
    print(f"  Business._meta.is_sti_base: {getattr(Business._meta, 'is_sti_base', 'NOT SET')}")
    print(f"  BusinessExtension._meta.proxy: {getattr(BusinessExtension._meta, 'proxy', 'NOT SET')}")
    print(f"  BusinessExtension._meta.is_sti_subclass: {getattr(BusinessExtension._meta, 'is_sti_subclass', 'NOT SET')}")
    
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    print(f"  Business table: {business_table}")
    print(f"  BusinessExtension table: {extension_table}")
    print(f"  Same table: {'✅ YES' if business_table == extension_table else '❌ NO'}")

    # Generate migrations
    print(f"\n🔧 Generating migrations...")
    try:
        call_command('makemigrations', 'augend_businesses', verbosity=2, interactive=False)
        print(f"✅ Migrations generated successfully")
    except Exception as e:
        print(f"❌ Migration generation failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

    # Find and display the generated migration
    migration_files = list(migrations_dir.glob('*.py'))
    migration_files = [f for f in migration_files if f.name != '__init__.py']
    
    if migration_files:
        migration_file = migration_files[0]
        print(f"\n📄 Generated Migration File: {migration_file.name}")
        print("=" * 80)
        
        with open(migration_file, 'r') as f:
            migration_content = f.read()
        
        print(migration_content)
        print("=" * 80)
        
        # Analyze the migration
        print(f"\n🔍 Migration Analysis:")
        
        lines = migration_content.split('\n')
        operations_section = False
        business_operation = None
        extension_operation = None
        
        for i, line in enumerate(lines):
            if 'operations = [' in line:
                operations_section = True
                continue
            
            if operations_section and 'CreateModel' in line:
                if "'Business'" in line or '"Business"' in line:
                    business_operation = i
                    print(f"  ✅ Found Business CreateModel at line {i+1}")
                elif "'BusinessExtension'" in line or '"BusinessExtension"' in line:
                    extension_operation = i
                    print(f"  ❌ Found BusinessExtension CreateModel at line {i+1}")
        
        has_onetoone = 'OneToOneField' in migration_content
        has_proxy = 'proxy' in migration_content.lower()
        
        print(f"  Creates Business table: {'✅ YES' if business_operation else '❌ NO'}")
        print(f"  Creates BusinessExtension table: {'❌ BAD' if extension_operation else '✅ GOOD'}")
        print(f"  Has OneToOneField (MTI): {'❌ BAD' if has_onetoone else '✅ GOOD'}")
        print(f"  Has proxy reference: {'✅ YES' if has_proxy else '❌ NO'}")
        
        print(f"\n🏁 Result:")
        if business_operation and not extension_operation and not has_onetoone:
            print(f"  🎉 SUCCESS! Correct STI migration generated")
        else:
            print(f"  ❌ FAILURE! Incorrect MTI migration generated")
            print(f"     This will create separate tables instead of STI")
    else:
        print(f"❌ No migration files found!")

finally:
    # Cleanup
    os.chdir('/')
    if str(project_dir) in sys.path:
        sys.path.remove(str(project_dir))
    shutil.rmtree(temp_dir)
    print(f"\n🧹 Cleaned up test project")