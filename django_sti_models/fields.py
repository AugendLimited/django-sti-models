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
    Enhanced CharField that stores the type name for STI models.

    Features:
    - Automatic type name validation
    - Dynamic choices based on registered types
    - Performance optimizations
    - Better error handling
    """

    def __init__(self, max_length: int = 100, *args: Any, **kwargs: Any) -> None:
        # Set sensible defaults for STI usage
        kwargs.setdefault("max_length", max_length)
        kwargs.setdefault("editable", False)  # Type field should not be user-editable
        kwargs.setdefault("db_index", True)  # Index for better query performance
        kwargs.setdefault("null", False)  # Type should always be set
        kwargs.setdefault("blank", False)  # Type should always be provided
        kwargs.setdefault("choices", [])  # Will be populated dynamically

        super().__init__(*args, **kwargs)

    def validate(self, value: Any, model_instance: Any) -> None:
        """Enhanced validation for type values."""
        super().validate(value, model_instance)

        if value is None:
            if not self.null:
                raise ValidationError(
                    _("Type field cannot be null."),
                    code="null_type",
                )
            return

        # Validate against registered types
        if model_instance is not None:
            registered_types = self._get_registered_types(model_instance)
            if registered_types and value not in registered_types:
                available_types = ', '.join(sorted(registered_types.keys()))
                raise ValidationError(
                    _('Type "%(type)s" is not registered. Available types: %(types)s'),
                    params={"type": value, "types": available_types},
                    code="invalid_type",
                )

    def _get_registered_types(self, model_instance: Any) -> dict:
        """Get registered types for a model instance."""
        # Try to get from the instance's base model
        if hasattr(model_instance, 'get_sti_base_model'):
            base_model = model_instance.get_sti_base_model()
            if base_model and hasattr(base_model._meta, "typed_models"):
                return base_model._meta.typed_models
        
        # Fallback to instance meta
        if hasattr(model_instance, "_meta") and hasattr(model_instance._meta, "typed_models"):
            return model_instance._meta.typed_models
            
        return {}

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
        registered_types = self._get_model_registered_types()
        if registered_types:
            type_choices = [(name, self._format_choice_label(name)) for name in sorted(registered_types.keys())]
            choices.extend(type_choices)

        return choices

    def _get_model_registered_types(self) -> dict:
        """Get registered types from the field's model."""
        if not hasattr(self, 'model') or self.model is None:
            return {}
            
        # Try different ways to access registered types
        if hasattr(self.model, 'get_sti_base_model'):
            base_model = self.model.get_sti_base_model()
            if base_model and hasattr(base_model._meta, "typed_models"):
                return base_model._meta.typed_models
        
        if hasattr(self.model._meta, "typed_models"):
            return self.model._meta.typed_models
            
        return {}

    def _format_choice_label(self, type_name: str) -> str:
        """Format the choice label for display."""
        # Convert CamelCase to Title Case with spaces
        import re
        formatted = re.sub(r'([A-Z])', r' \1', type_name).strip()
        return formatted

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
