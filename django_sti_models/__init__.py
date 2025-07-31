"""
Django STI Models - Improved Single Table Inheritance for Django

A modern, type-safe implementation of Single Table Inheritance (STI) for Django
with improved monkey patching and better performance.
"""

__version__ = "0.1.9"
__author__ = "Konrad Beck"
__email__ = "konrad.beck@gmail.com"

from .exceptions import STIException
from .fields import TypeField
from .models import TypedModel, TypedModelManager
from .utils import (
    create_typed_instance,
    filter_by_type,
    get_type_field_value,
    get_type_hierarchy,
    get_type_statistics,
    get_typed_model_classes,
    get_typed_queryset,
    is_typed_instance,
    migrate_type_field,
    validate_type_consistency,
    validate_type_registration,
)

__all__ = [
    # Core classes
    "TypedModel",
    "TypedModelManager",
    "TypeField",
    "STIException",
    # Utility functions
    "get_typed_queryset",
    "create_typed_instance",
    "get_type_hierarchy",
    "validate_type_registration",
    "get_type_field_value",
    "is_typed_instance",
    "get_typed_model_classes",
    "filter_by_type",
    "get_type_statistics",
    "migrate_type_field",
    "validate_type_consistency",
]

# Lazy imports for admin classes to avoid circular imports
def get_admin_classes():
    """Get admin classes with lazy loading to avoid circular imports."""
    from .admin import (
        TypedModelAdmin,
        TypedModelAdminMixin,
        TypedModelForm,
        TypeFilter,
        create_typed_admin_class,
        register_typed_models,
    )
    return {
        "TypedModelAdmin": TypedModelAdmin,
        "TypedModelAdminMixin": TypedModelAdminMixin,
        "TypedModelForm": TypedModelForm,
        "TypeFilter": TypeFilter,
        "create_typed_admin_class": create_typed_admin_class,
        "register_typed_models": register_typed_models,
    }

# Post-initialization setup for STI models
def setup_sti_models():
    """Set up STI models after Django is ready."""
    try:
        from django.apps import apps
        if apps.ready:
            print("🚀 Setting up STI models after Django initialization...")
            from django.db import models
            
            # Find all models that need STI setup
            for app_config in apps.get_app_configs():
                for model in app_config.get_models():
                    if hasattr(model, '_needs_sti_setup') and model._needs_sti_setup:
                        model._setup_sti_post_init()
            
            print("✅ STI models setup complete!")
    except Exception as e:
        print(f"⚠️ Error setting up STI models: {e}")

# Register the setup function to run after Django is ready
try:
    from django.apps import apps
    if apps.ready:
        setup_sti_models()
    else:
        # Register for when apps become ready
        from django.apps import AppConfig
        original_ready = AppConfig.ready
        
        def ready_with_sti(self):
            original_ready(self)
            setup_sti_models()
        
        AppConfig.ready = ready_with_sti
except ImportError:
    # Django not available yet
    pass
