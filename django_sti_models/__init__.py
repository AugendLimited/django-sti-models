"""
Django STI Models - Improved Single Table Inheritance for Django

A modern, type-safe implementation of Single Table Inheritance (STI) for Django
with improved monkey patching and better performance.
"""

__version__ = "0.1.5"
__author__ = "Konrad Beck"
__email__ = "konrad.beck@gmail.com"

from .admin import (
    TypedModelAdmin,
    TypedModelAdminMixin,
    TypedModelForm,
    TypeFilter,
    create_typed_admin_class,
    register_typed_models,
)
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
    # Admin integration
    "TypedModelAdmin",
    "TypedModelAdminMixin",
    "TypedModelForm",
    "TypeFilter",
    "register_typed_models",
    "create_typed_admin_class",
]
