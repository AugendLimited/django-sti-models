"""
Simple and robust Single Table Inheritance for Django.

This implementation provides clean STI with:
- Automatic table sharing for subclasses
- Type-aware querying and management
- Support for both concrete and abstract base classes
- Custom type field names
"""

from typing import Any, Dict, Optional, Type, TypeVar

from django.db import models
from django.db.models.base import ModelBase
from django.db.models.manager import Manager

from .fields import TypeField

T = TypeVar("T", bound="TypedModel")


class TypedModelManager(Manager[T]):
    """Simple manager for TypedModel with type-aware querying."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.model_class: Optional[Type[T]] = None

    def contribute_to_class(self, model: Type[T], name: str) -> None:
        """Called when manager is added to a model class."""
        super().contribute_to_class(model, name)
        self.model_class = model
        # Ensure the model property is also set for Django's manager
        self.model = model

    def get_queryset(self) -> models.QuerySet[T]:
        """Get a queryset, filtered by type for subclasses."""
        queryset = super().get_queryset()

        # If this is a subclass of a TypedModel, filter by type
        if (
            self.model_class
            and hasattr(self.model_class, "_meta")
            and getattr(self.model_class._meta, "is_sti_subclass", False)
        ):
            type_field_name = self._get_type_field_name()
            if type_field_name:
                type_name = self.model_class.__name__
                queryset = queryset.filter(**{type_field_name: type_name})

        return queryset

    def _get_type_field_name(self) -> Optional[str]:
        """Get the type field name for this model."""
        if not self.model_class:
            return None

        # Check meta first
        if hasattr(self.model_class._meta, "type_field_name"):
            return self.model_class._meta.type_field_name

        # Look for TypeField in model or its bases
        try:
            for field in self.model_class._meta.get_fields():
                if isinstance(field, TypeField):
                    return field.name
        except Exception:
            # Fallback to default
            return "model_type"

        return None

    def create(self, **kwargs: Any) -> T:
        """Create a new instance with the correct type."""
        type_field_name = self._get_type_field_name()

        if type_field_name and type_field_name not in kwargs and self.model_class:
            kwargs[type_field_name] = self.model_class.__name__

        return super().create(**kwargs)


class TypedModelMeta(ModelBase):
    """Metaclass for STI models using Django's class_prepared signal approach."""

    def __new__(
        mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs: Any
    ) -> Type[T]:
        """Create a new typed model class."""
        
        # Create the class normally - let Django handle inheritance
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        
        # Connect to class_prepared signal to set up STI after Django is done
        models.signals.class_prepared.connect(mcs._setup_sti_after_prepared, sender=cls)
        
        return cls

    @classmethod
    def _setup_sti_after_prepared(mcs, sender: Type[T], **kwargs: Any) -> None:
        """Set up STI after Django has prepared the model class."""
        
        # Skip abstract models - they don't create tables
        if getattr(sender._meta, "abstract", False):
            return
            
        # Skip TypedModel itself
        if sender.__name__ == "TypedModel":
            return
            
        # Check if this model has a TypeField (either declared or inherited)
        has_type_field = mcs._has_type_field(sender)
        
        if has_type_field:
            # This is an STI base model
            mcs._setup_sti_base(sender)
        else:
            # Check if this inherits from an STI base
            sti_base = mcs._find_sti_base(sender)
            if sti_base:
                mcs._setup_sti_subclass(sender, sti_base)

    @classmethod
    def _has_type_field(mcs, cls: Type[T]) -> bool:
        """Check if a class has a TypeField."""
        try:
            for field in cls._meta.get_fields():
                if isinstance(field, TypeField):
                    return True
        except Exception:
            # Fallback to check declared fields
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name, None)
                if isinstance(attr, TypeField):
                    return True
        return False

    @classmethod
    def _find_sti_base(mcs, cls: Type[T]) -> Optional[Type[T]]:
        """Find the STI base class for this model."""
        for base in cls.__bases__:
            if hasattr(base, "_meta") and getattr(base._meta, "is_sti_base", False):
                return base
        return None

    @classmethod
    def _setup_sti_base(mcs, cls: Type[T]) -> None:
        """Set up a base STI model."""
        cls._meta.is_sti_base = True

        # Find type field name
        type_field_name = None
        try:
            for field in cls._meta.get_fields():
                if isinstance(field, TypeField):
                    type_field_name = field.name
                    break
        except Exception:
            # Fallback if get_fields() fails
            type_field_name = "model_type"

        if type_field_name:
            cls._meta.type_field_name = type_field_name
            cls._meta.typed_models = {cls.__name__: cls}

        # Set up manager and properly initialize it
        manager = TypedModelManager()
        manager.contribute_to_class(cls, "objects")
        cls.objects = manager

    @classmethod
    def _setup_sti_subclass(mcs, cls: Type[T], base: Type[T]) -> None:
        """Set up an STI subclass using Django's proxy model approach."""
        cls._meta.is_sti_subclass = True
        cls._meta.sti_base_model = base

        # Force proxy=True for STI behavior
        cls._meta.proxy = True

        # Register with base model
        if hasattr(base._meta, "typed_models"):
            base._meta.typed_models[cls.__name__] = cls

        # Share type field name
        if hasattr(base._meta, "type_field_name"):
            cls._meta.type_field_name = base._meta.type_field_name

        # Set up manager and properly initialize it
        manager = TypedModelManager()
        manager.contribute_to_class(cls, "objects")
        cls.objects = manager


class TypedModel(models.Model, metaclass=TypedModelMeta):
    """Simple base class for Single Table Inheritance (STI) models."""

    # Default type field - subclasses can override the field name
    model_type = TypeField()

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the model, ensuring the type field is set."""
        # Set the type field to the current class name
        type_field_name = self.get_type_field_name()
        if type_field_name:
            setattr(self, type_field_name, self.__class__.__name__)

        super().save(*args, **kwargs)

    @classmethod
    def get_type_field_name(cls) -> str:
        """Get the name of the type field for this model."""
        if hasattr(cls._meta, "type_field_name"):
            return cls._meta.type_field_name
        return "model_type"

    @classmethod
    def get_all_types(cls) -> Dict[str, Type[T]]:
        """Get all registered types for this STI hierarchy."""
        if hasattr(cls._meta, "typed_models"):
            return cls._meta.typed_models.copy()
        return {}

    @classmethod
    def get_type_class(cls, type_name: str) -> Optional[Type[T]]:
        """Get the model class for a given type name."""
        if hasattr(cls._meta, "typed_models"):
            return cls._meta.typed_models.get(type_name)
        return None
