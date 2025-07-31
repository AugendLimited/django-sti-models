#!/usr/bin/env python
"""
Test that TypeField inheritance from abstract base classes works correctly.
"""

import os
import sys
import django
from django.conf import settings

# Configure minimal Django
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        USE_TZ=True,
    )

django.setup()

# Import after Django setup
from django.db import models, connection
from django_sti_models import TypedModel, TypeField


class AbstractBaseWithTypeField(TypedModel):
    """Abstract base class with TypeField that should be inherited."""
    model_type = TypeField()
    
    class Meta:
        abstract = True
        app_label = 'test'


class ConcreteModel(AbstractBaseWithTypeField):
    """Concrete model that inherits TypeField from abstract base."""
    name = models.CharField(max_length=255)
    
    class Meta:
        app_label = 'test'
    
    def __str__(self):
        return self.name


class ConcreteSubclass(ConcreteModel):
    """Subclass of the concrete model."""
    description = models.TextField(blank=True, default="")
    
    class Meta:
        app_label = 'test'
    
    def __str__(self):
        return f"{self.name} - {self.description}"


def test_abstract_inheritance():
    """Test that TypeField inheritance from abstract bases works."""
    print("🧪 Testing Abstract Inheritance with TypeField\n")
    
    # Check that the concrete model has the type field
    print("📝 Checking ConcreteModel type field:")
    assert hasattr(ConcreteModel._meta, 'type_field_name'), "ConcreteModel should have type_field_name"
    assert ConcreteModel._meta.type_field_name == 'model_type', "Type field name should be 'model_type'"
    print("  ✅ ConcreteModel has type_field_name")
    
    # Check that it's marked as an STI base
    assert getattr(ConcreteModel._meta, 'is_sti_base', False), "ConcreteModel should be marked as STI base"
    print("  ✅ ConcreteModel is marked as STI base")
    
    # Check that it has typed_models registry
    assert hasattr(ConcreteModel._meta, 'typed_models'), "ConcreteModel should have typed_models registry"
    assert 'ConcreteModel' in ConcreteModel._meta.typed_models, "ConcreteModel should be in typed_models"
    print("  ✅ ConcreteModel has typed_models registry")
    
    # Check that subclass is marked as STI subclass
    print("\n📝 Checking ConcreteSubclass:")
    assert getattr(ConcreteSubclass._meta, 'is_sti_subclass', False), "ConcreteSubclass should be marked as STI subclass"
    print("  ✅ ConcreteSubclass is marked as STI subclass")
    
    # Check that it's a proxy model
    assert ConcreteSubclass._meta.proxy, "ConcreteSubclass should be a proxy model"
    print("  ✅ ConcreteSubclass is a proxy model")
    
    # Check that it shares the same type field name
    assert ConcreteSubclass._meta.type_field_name == 'model_type', "Subclass should share type field name"
    print("  ✅ ConcreteSubclass shares type field name")
    
    # Check that it's registered with the base
    assert 'ConcreteSubclass' in ConcreteModel._meta.typed_models, "ConcreteSubclass should be registered"
    print("  ✅ ConcreteSubclass is registered with base")
    
    # Create table and test instances
    print("\n🏗️ Creating Table and Testing Instances:")
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ConcreteModel)
        print("  ✅ Table created")
        
        # Test instance creation
        concrete = ConcreteModel.objects.create(name="Test Concrete")
        subclass = ConcreteSubclass.objects.create(name="Test Subclass", description="Test")
        
        print(f"  ✅ Concrete created: {concrete} (type: {concrete.model_type})")
        print(f"  ✅ Subclass created: {subclass} (type: {subclass.model_type})")
        
        # Check that type fields are set correctly
        assert concrete.model_type == "ConcreteModel", "Concrete model type should be 'ConcreteModel'"
        assert subclass.model_type == "ConcreteSubclass", "Subclass model type should be 'ConcreteSubclass'"
        print("  ✅ Type fields set correctly")
        
        # Test that each model only returns its own type
        concrete_queryset = ConcreteModel.objects.all()
        subclass_queryset = ConcreteSubclass.objects.all()
        
        print(f"  📊 Query debugging:")
        print(f"    ConcreteModel queryset count: {concrete_queryset.count()}")
        print(f"    ConcreteSubclass queryset count: {subclass_queryset.count()}")
        print(f"    ConcreteModel SQL: {concrete_queryset.query}")
        print(f"    ConcreteSubclass SQL: {subclass_queryset.query}")
        
        # Debug: Check all objects in the table
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {ConcreteModel._meta.db_table}")
        rows = cursor.fetchall()
        print(f"    All rows in table: {rows}")
        
        assert concrete_queryset.count() == 1, "ConcreteModel queryset should have 1 item"
        assert subclass_queryset.count() == 1, "ConcreteSubclass queryset should have 1 item"
        
        assert concrete_queryset.first() == concrete, "ConcreteModel queryset should return concrete instance"
        assert subclass_queryset.first() == subclass, "ConcreteSubclass queryset should return subclass instance"
        print("  ✅ Queryset filtering works correctly")
        
        # Test get_all_types
        all_types = ConcreteModel.get_all_types()
        assert 'ConcreteModel' in all_types, "ConcreteModel should be in all_types"
        assert 'ConcreteSubclass' in all_types, "ConcreteSubclass should be in all_types"
        assert all_types['ConcreteModel'] == ConcreteModel, "ConcreteModel should map to ConcreteModel class"
        assert all_types['ConcreteSubclass'] == ConcreteSubclass, "ConcreteSubclass should map to ConcreteSubclass class"
        print("  ✅ get_all_types works correctly")
        
        print("\n🎉 All tests passed! Abstract inheritance with TypeField works correctly.")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        raise


if __name__ == "__main__":
    test_abstract_inheritance() 