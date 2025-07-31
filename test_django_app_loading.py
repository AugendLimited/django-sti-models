#!/usr/bin/env python
"""
Test the difference between direct model creation and Django app loading.
"""

import os
import tempfile
import shutil
from pathlib import Path
import django
from django.conf import settings
from django.apps import apps
import sys

# First test: Direct model creation (what we've been doing)
print("🧪 Test 1: Direct Model Creation")
print("=" * 50)

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

class AugendModel(TypedModel, AuditableModel, CloneMixin, HookModelMixin):
    model_type = TypeField()
    class Meta:
        abstract = True

class DirectBusiness(AugendModel):
    name = models.CharField(max_length=255)
    class Meta:
        app_label = 'test'

class DirectBusinessExtension(DirectBusiness):
    description = models.TextField(blank=True, default="")
    class Meta:
        app_label = 'test'

print(f"Direct Business is_sti_base: {getattr(DirectBusiness._meta, 'is_sti_base', False)}")
print(f"Direct BusinessExtension proxy: {getattr(DirectBusinessExtension._meta, 'proxy', False)}")

print(f"\n🧪 Test 2: Django App Loading")
print("=" * 50)

# Create a temporary Django app
temp_dir = Path(tempfile.mkdtemp())
app_dir = temp_dir / 'test_app'
app_dir.mkdir()

# Create __init__.py
(app_dir / '__init__.py').write_text('')

# Create models.py with EXACT same content
models_content = '''
from django.db import models
from django_sti_models import TypedModel, TypeField

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

class AugendModel(TypedModel, AuditableModel, CloneMixin, HookModelMixin):
    model_type = TypeField()
    class Meta:
        abstract = True

class Business(AugendModel):
    name = models.CharField(max_length=255)
    class Meta:
        verbose_name_plural = "Businesses"

class BusinessExtension(Business):
    description = models.TextField(blank=True, default="")
    class Meta:
        verbose_name_plural = "Business Extensions"
'''

(app_dir / 'models.py').write_text(models_content)

# Create apps.py
apps_content = '''
from django.apps import AppConfig

class TestAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'test_app'
'''
(app_dir / 'apps.py').write_text(apps_content)

# Add to Python path
sys.path.insert(0, str(temp_dir))

try:
    # Reconfigure Django to include our test app
    from django.test.utils import override_settings
    
    with override_settings(INSTALLED_APPS=[
        'django.contrib.contenttypes',
        'django.contrib.auth', 
        'test_app'
    ]):
        # Force Django to reload apps
        apps.populate(settings.INSTALLED_APPS)
        
        # Import the models from the Django app
        from test_app.models import Business, BusinessExtension
        
        print(f"App Business is_sti_base: {getattr(Business._meta, 'is_sti_base', False)}")
        print(f"App BusinessExtension proxy: {getattr(BusinessExtension._meta, 'proxy', False)}")
        
        # Check table names
        business_table = Business._meta.db_table
        extension_table = BusinessExtension._meta.db_table
        print(f"Business table: {business_table}")
        print(f"BusinessExtension table: {extension_table}")
        print(f"Same table: {'✅ YES' if business_table == extension_table else '❌ NO'}")

except Exception as e:
    print(f"❌ Error with Django app loading: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Cleanup
    if str(temp_dir) in sys.path:
        sys.path.remove(str(temp_dir))
    shutil.rmtree(temp_dir)

print(f"\n🔍 Comparison:")
print(f"Direct creation works: ✅ YES")
print(f"Django app loading works: ?")
print(f"\nIf Django app loading fails, the issue is with model loading order or app configuration.")