"""
Django Admin integration for STI Models.
"""

from typing import Any, Dict, List, Optional, Type, Union

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.db import models
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import TypedModel
from .utils import get_type_statistics, validate_type_consistency


class TypedModelForm(ModelForm):
    """
    Form for typed models that handles type field validation.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        # Set type field choices if this is a typed model
        if hasattr(self.Meta.model, "get_all_types"):
            type_field_name = self.Meta.model.get_type_field_name()
            if type_field_name in self.fields:
                registered_types = self.Meta.model.get_all_types()
                choices = [(name, name) for name in registered_types.keys()]
                self.fields[type_field_name].choices = choices


class TypedModelAdmin(ModelAdmin):
    """
    Base admin class for typed models.

    This admin class provides:
    - Type-aware filtering
    - Type statistics
    - Validation tools
    - Better form handling
    """

    form = TypedModelForm
    list_filter = ("type",)
    readonly_fields = ("type",)

    def get_list_filter(self, request: Any) -> List[Any]:
        """Get list filters, including type filter."""
        filters = list(super().get_list_filter(request))

        # Add type filter if not already present
        type_filter_name = self.model.get_type_field_name()
        if type_filter_name not in filters:
            filters.append(type_filter_name)

        return filters

    def get_queryset(self, request: Any) -> models.QuerySet:
        """Get queryset with type-aware filtering."""
        queryset = super().get_queryset(request)

        # If this is a specific type admin, filter by type
        if hasattr(self.model, "_meta") and hasattr(self.model._meta, "typed_models"):
            # This is a specific type, so filter by type
            type_name = self.model.__name__
            type_field_name = self.model.get_type_field_name()
            queryset = queryset.filter(**{type_field_name: type_name})

        return queryset

    def get_readonly_fields(self, request: Any, obj: Optional[Any] = None) -> List[str]:
        """Get readonly fields, ensuring type field is readonly."""
        readonly_fields = list(super().get_readonly_fields(request, obj))

        # Ensure type field is readonly
        type_field_name = self.model.get_type_field_name()
        if type_field_name not in readonly_fields:
            readonly_fields.append(type_field_name)

        return readonly_fields

    def save_model(self, request: Any, obj: Any, form: Any, change: bool) -> None:
        """Save the model, ensuring type field is set."""
        # Ensure type field is set
        if not change:  # Only for new objects
            type_field_name = self.model.get_type_field_name()
            if not getattr(obj, type_field_name, None):
                setattr(obj, type_field_name, self.model.__name__)

        super().save_model(request, obj, form, change)


class TypedModelAdminMixin:
    """
    Mixin for admin classes that provides typed model functionality.
    """

    def get_type_statistics(self) -> Dict[str, int]:
        """Get type statistics for the model."""
        return get_type_statistics(self.model)

    def validate_type_consistency(self) -> List[str]:
        """Validate type consistency for the model."""
        return validate_type_consistency(self.model)

    def get_type_choices(self) -> List[tuple]:
        """Get choices for type field."""
        registered_types = self.model.get_all_types()
        return [(name, name) for name in registered_types.keys()]


def register_typed_models(
    base_model: Type[TypedModel], admin_site: Optional[admin.AdminSite] = None
) -> None:
    """
    Register all typed models with the admin site.

    Args:
        base_model: The base typed model class
        admin_site: The admin site to register with (defaults to admin.site)
    """
    if admin_site is None:
        admin_site = admin.site

    registered_types = base_model.get_all_types()

    for type_name, type_class in registered_types.items():
        # Create a dynamic admin class for this type
        admin_class_name = f"{type_name}Admin"
        admin_class = type(
            admin_class_name,
            (TypedModelAdmin,),
            {
                "model": type_class,
                "list_display": ["__str__", "type"],
                "search_fields": ["name"] if hasattr(type_class, "name") else [],
            },
        )

        # Register the admin class
        admin_site.register(type_class, admin_class)


class TypeFilter(admin.SimpleListFilter):
    """
    Admin filter for type fields.
    """

    title = _("Type")
    parameter_name = "type"

    def lookups(self, request: Any, model_admin: Any) -> List[tuple]:
        """Get filter choices."""
        if hasattr(model_admin.model, "get_all_types"):
            registered_types = model_admin.model.get_all_types()
            return [(name, name) for name in registered_types.keys()]
        return []

    def queryset(self, request: Any, queryset: models.QuerySet) -> models.QuerySet:
        """Filter the queryset."""
        if self.value():
            type_field_name = queryset.model.get_type_field_name()
            return queryset.filter(**{type_field_name: self.value()})
        return queryset


def create_typed_admin_class(
    model_class: Type[TypedModel],
    base_admin_class: Type[ModelAdmin] = TypedModelAdmin,
    **kwargs: Any,
) -> Type[ModelAdmin]:
    """
    Create an admin class for a typed model.

    Args:
        model_class: The typed model class
        base_admin_class: The base admin class to inherit from
        **kwargs: Additional attributes for the admin class

    Returns:
        An admin class for the typed model
    """
    admin_class_name = f"{model_class.__name__}Admin"

    # Default attributes
    default_attrs = {
        "model": model_class,
        "list_display": ["__str__", model_class.get_type_field_name()],
        "list_filter": [TypeFilter],
        "readonly_fields": [model_class.get_type_field_name()],
    }

    # Merge with provided kwargs
    attrs = {**default_attrs, **kwargs}

    return type(admin_class_name, (base_admin_class,), attrs)
