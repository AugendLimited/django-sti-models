"""
Type field implementation for Django STI Models.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Type, Union

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .exceptions import InvalidTypeError


class TypeField(models.CharField):
    """
    A CharField that stores the type name for STI models.

    This field automatically manages the type name storage and provides
    validation for registered types.
    """

    def __init__(self, max_length: int = 100, *args: Any, **kwargs: Any) -> None:
        # Set a reasonable default max_length for type names
        kwargs.setdefault("max_length", max_length)
        kwargs.setdefault("editable", False)  # Type field should not be editable
        kwargs.setdefault("db_index", True)  # Index for better query performance
        kwargs.setdefault("choices", [])  # Will be populated dynamically

        super().__init__(*args, **kwargs)

    def validate(self, value: Any, model_instance: Any) -> None:
        """Validate the type value."""
        super().validate(value, model_instance)

        if value is None:
            return

        # Check if the type is registered (if we have access to the model)
        if hasattr(model_instance, "_meta") and hasattr(
            model_instance._meta, "typed_models"
        ):
            registered_types = model_instance._meta.typed_models
            if value not in registered_types:
                raise ValidationError(
                    _('Type "%(type)s" is not registered for this model.'),
                    params={"type": value},
                    code="invalid_type",
                )

    def get_prep_value(self, value: Any) -> Optional[str]:
        """Prepare the value for database storage."""
        if value is None:
            return None

        # Ensure we store the type name as a string
        if isinstance(value, type):
            return value.__name__
        return str(value)

    def from_db_value(
        self, value: Any, expression: Any, connection: Any
    ) -> Optional[str]:
        """Convert database value to Python value."""
        return value

    def to_python(self, value: Any) -> Optional[str]:
        """Convert input value to Python value."""
        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, type):
            return value.__name__

        return str(value)

    def get_choices(
        self, include_blank: bool = True, blank_choice: Optional[List[tuple]] = None
    ) -> List[tuple]:
        """Get choices for the field, including registered types."""
        choices = super().get_choices(
            include_blank=include_blank, blank_choice=blank_choice
        )

        # Try to get registered types from the model
        if hasattr(self.model, "_meta") and hasattr(self.model._meta, "typed_models"):
            registered_types = self.model._meta.typed_models
            type_choices = [(name, name) for name in registered_types.keys()]
            choices.extend(type_choices)

        return choices

    @lru_cache(maxsize=128)
    def _get_registered_types(self, model_class: Type) -> Set[str]:
        """Get registered types for a model class (cached)."""
        if hasattr(model_class, "_meta") and hasattr(model_class._meta, "typed_models"):
            return set(model_class._meta.typed_models.keys())
        return set()

    def formfield(self, **kwargs: Any) -> Any:
        """Get the form field for this model field."""
        from django import forms

        # Add choices if we have registered types
        if hasattr(self.model, "_meta") and hasattr(self.model._meta, "typed_models"):
            registered_types = self.model._meta.typed_models
            kwargs.setdefault(
                "choices", [(name, name) for name in registered_types.keys()]
            )

        return super().formfield(**kwargs)
