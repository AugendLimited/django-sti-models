"""
Core TypedModel implementation with improved monkey patching.
"""

import weakref
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, cast

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.manager import Manager
from django.utils.translation import gettext_lazy as _

from .exceptions import (
    CircularInheritanceError,
    STIException,
    TypeFieldNotFoundError,
    TypeRegistrationError,
)
from .fields import TypeField

T = TypeVar("T", bound="TypedModel")
BaseT = TypeVar("BaseT", bound="TypedModel")


class TypedModelManager(Manager[T]):
    """
    Manager for TypedModel that provides type-aware querying.

    This manager automatically filters by the correct type when
    querying on typed model subclasses.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._typed_model_class: Optional[Type[T]] = None

    def _set_typed_model_class(self, model_class: Type[T]) -> None:
        """Set the typed model class for this manager."""
        self._typed_model_class = model_class

    def get_queryset(self) -> models.QuerySet[T]:
        """Get a queryset filtered by the correct type."""
        queryset = super().get_queryset()

        if self._typed_model_class is not None:
            # Filter by the type field to only return instances of this specific type
            type_field_name = self._typed_model_class._meta.type_field_name
            type_name = self._typed_model_class.__name__
            queryset = queryset.filter(**{type_field_name: type_name})

        return queryset

    def create(self, **kwargs: Any) -> T:
        """Create a new instance with the correct type."""
        if self._typed_model_class is not None:
            type_field_name = self._typed_model_class._meta.type_field_name
            if type_field_name not in kwargs:
                kwargs[type_field_name] = self._typed_model_class.__name__

        return super().create(**kwargs)

    def get_or_create(
        self, defaults: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> tuple[T, bool]:
        """Get or create an instance with the correct type."""
        if self._typed_model_class is not None:
            type_field_name = self._typed_model_class._meta.type_field_name
            if type_field_name not in kwargs:
                kwargs[type_field_name] = self._typed_model_class.__name__

            if defaults is None:
                defaults = {}
            if type_field_name not in defaults:
                defaults[type_field_name] = self._typed_model_class.__name__

        return super().get_or_create(defaults=defaults, **kwargs)

    def update_or_create(
        self, defaults: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> tuple[T, bool]:
        """Update or create an instance with the correct type."""
        if self._typed_model_class is not None:
            type_field_name = self._typed_model_class._meta.type_field_name
            if type_field_name not in kwargs:
                kwargs[type_field_name] = self._typed_model_class.__name__

            if defaults is None:
                defaults = {}
            if type_field_name not in defaults:
                defaults[type_field_name] = self._typed_model_class.__name__

        return super().update_or_create(defaults=defaults, **kwargs)


class TypedModelMeta(ModelBase):
    """
    Metaclass for TypedModel that handles type registration and field setup.

    This metaclass improves upon the original by:
    1. Better error handling and validation
    2. More efficient type registration
    3. Cleaner monkey patching
    4. Type safety improvements
    """

    def __new__(
        mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs: Any
    ) -> Type[T]:
        """Create a new typed model class."""
        # Check for circular inheritance
        if name in [base.__name__ for base in bases if hasattr(base, "__name__")]:
            raise CircularInheritanceError(
                f"Circular inheritance detected for model '{name}'"
            )

        # Create the class
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Skip processing for abstract models
        if namespace.get("Meta", {}).get("abstract", False):
            return cls

        # Process typed models
        # Check if any base is a TypedModel by checking for the model_type field
        # Only process if Django's app registry is ready
        try:
            from django.apps import apps
            apps.check_apps_ready()
            
            has_typed_model_base = any(
                hasattr(base, '_meta') and 
                hasattr(base._meta, 'fields_map') and
                any(isinstance(field, TypeField) for field in base._meta.fields_map.values())
                for base in bases
            )
        except Exception:
            # Django app registry not ready, skip processing
            has_typed_model_base = False
        
        if has_typed_model_base:
            mcs._setup_typed_model(cls)

        return cls

    @classmethod
    def _setup_typed_model(mcs, cls: Type[T]) -> None:
        """Set up a typed model with proper field configuration."""
        # Only process if Django's app registry is ready
        try:
            from django.apps import apps
            apps.check_apps_ready()
        except Exception:
            # Django app registry not ready, skip processing
            return
            
        # Find the base typed model (the one that has a TypeField)
        base_typed_model = None
        for base in cls.__mro__:
            if (base is not cls and 
                hasattr(base, '_meta') and 
                hasattr(base._meta, 'fields_map') and
                any(isinstance(field, TypeField) for field in base._meta.fields_map.values())):
                base_typed_model = base
                break

        if base_typed_model is None:
            return

        # Set up the type field
        mcs._setup_type_field(cls, base_typed_model)

        # Register the type
        mcs._register_type(cls, base_typed_model)

        # Set up the manager
        mcs._setup_manager(cls)

    @classmethod
    def _setup_type_field(mcs, cls: Type[T], base_typed_model: Type[T]) -> None:
        """Set up the type field for the model."""
        # Only process if Django's app registry is ready
        try:
            from django.apps import apps
            apps.check_apps_ready()
        except Exception:
            # Django app registry not ready, skip processing
            return
            
        # Find the type field in the base model
        type_field_name = None
        for field_name, field in base_typed_model._meta.fields_map.items():
            if isinstance(field, TypeField):
                type_field_name = field_name
                break

        if type_field_name is None:
            raise TypeFieldNotFoundError(
                f"No TypeField found in base model {base_typed_model.__name__}"
            )

        # Store the type field name for later use
        cls._meta.type_field_name = type_field_name

        # Ensure the type field is not editable
        if hasattr(cls._meta, "fields_map") and type_field_name in cls._meta.fields_map:
            field = cls._meta.fields_map[type_field_name]
            field.editable = False

    @classmethod
    def _register_type(mcs, cls: Type[T], base_typed_model: Type[T]) -> None:
        """Register the type with the base model."""
        # Only process if Django's app registry is ready
        try:
            from django.apps import apps
            apps.check_apps_ready()
        except Exception:
            # Django app registry not ready, skip processing
            return
            
        # Initialize typed_models if it doesn't exist
        if not hasattr(base_typed_model._meta, "typed_models"):
            base_typed_model._meta.typed_models = {}

        # Register this type
        type_name = cls.__name__
        base_typed_model._meta.typed_models[type_name] = cls

        # Store a reference to the base model
        cls._meta.base_typed_model = base_typed_model

    @classmethod
    def _setup_manager(mcs, cls: Type[T]) -> None:
        """Set up the manager for the typed model."""
        # Only process if Django's app registry is ready
        try:
            from django.apps import apps
            apps.check_apps_ready()
        except Exception:
            # Django app registry not ready, skip processing
            return
            
        # Create a new manager instance
        manager = TypedModelManager()
        manager._set_typed_model_class(cls)

        # Replace the default manager
        cls.objects = manager

        # Also set it as the default manager
        if not hasattr(cls._meta, "default_manager"):
            cls._meta.default_manager = manager


class TypedModel(models.Model, metaclass=TypedModelMeta):
    """
    Base class for Single Table Inheritance (STI) models.

    This implementation improves upon the original django-typed-models by:
    1. Better monkey patching with cleaner metaclass implementation
    2. Improved type safety with proper type hints
    3. More efficient type registration and lookup
    4. Better error handling and validation
    5. Cleaner manager implementation
    """

    # Type field - subclasses should override this with their own TypeField
    # Use a more descriptive name like 'model_type', 'content_type', etc.
    model_type = TypeField()

    class Meta:
        abstract = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the typed model."""
        # Set the type field if not provided
        type_field_name = self.get_type_field_name()
        if type_field_name not in kwargs:
            kwargs[type_field_name] = self.__class__.__name__

        super().__init__(*args, **kwargs)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the model, ensuring the type field is set."""
        # Ensure the type field is set
        type_field_name = self.get_type_field_name()
        if not hasattr(self, type_field_name) or not getattr(self, type_field_name):
            setattr(self, type_field_name, self.__class__.__name__)

        super().save(*args, **kwargs)

    @classmethod
    def get_type_class(cls, type_name: str) -> Optional[Type[T]]:
        """Get the class for a given type name."""
        if hasattr(cls._meta, "typed_models"):
            return cls._meta.typed_models.get(type_name)
        return None

    @classmethod
    def get_all_types(cls) -> Dict[str, Type[T]]:
        """Get all registered types for this model."""
        if hasattr(cls._meta, "typed_models"):
            return cls._meta.typed_models.copy()
        return {}

    def get_real_instance(self) -> T:
        """Get the real instance of the correct type."""
        type_field_name = self.get_type_field_name()
        if not hasattr(self, type_field_name) or not getattr(self, type_field_name):
            return self

        type_class = self.get_type_class(getattr(self, type_field_name))
        if type_class is None:
            return self

        # Return a new instance of the correct type with the same data
        return type_class.objects.get(pk=self.pk)

    @classmethod
    def from_db(cls, db: str, field_names: List[str], values: List[Any]) -> T:
        """Create an instance from database values."""
        instance = super().from_db(db, field_names, values)

        # Convert to the correct type if possible
        type_field_name = cls.get_type_field_name()
        if hasattr(instance, type_field_name) and getattr(instance, type_field_name):
            type_class = cls.get_type_class(getattr(instance, type_field_name))
            if type_class is not None and type_class is not cls:
                # Create a new instance of the correct type
                return type_class.from_db(db, field_names, values)

        return instance

    @classmethod
    def get_type_field_name(cls) -> str:
        """Get the name of the type field for this model."""
        if hasattr(cls._meta, "type_field_name"):
            return cls._meta.type_field_name
        return "model_type"  # Default to a more descriptive name

    @classmethod
    def is_typed_model(cls) -> bool:
        """Check if this is a typed model."""
        return hasattr(cls._meta, "typed_models")

    @classmethod
    def get_base_typed_model(cls) -> Optional[Type[T]]:
        """Get the base typed model for this class."""
        if hasattr(cls._meta, "base_typed_model"):
            return cls._meta.base_typed_model
        return None
