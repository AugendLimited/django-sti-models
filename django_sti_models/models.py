"""
Simple and robust Single Table Inheritance for Django.

This implementation provides clean STI with:
- Automatic table sharing for subclasses
- Type-aware querying and management
- Support for both concrete and abstract base classes
- Custom type field names
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.manager import Manager
from django.utils.translation import gettext_lazy as _

from .exceptions import STIException
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
        if (self.model_class and 
            hasattr(self.model_class, '_meta') and
            getattr(self.model_class._meta, 'is_sti_subclass', False)):
            
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
        if hasattr(self.model_class._meta, 'type_field_name'):
            return self.model_class._meta.type_field_name
            
        # Look for TypeField in model or its bases
        try:
            for field in self.model_class._meta.get_fields():
                if isinstance(field, TypeField):
                    return field.name
        except:
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
    """Simple metaclass for STI models using proxy approach."""

    def __new__(
        mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs: Any
    ) -> Type[T]:
        """Create a new typed model class."""
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Skip abstract models and TypedModel itself
        if (getattr(getattr(cls, 'Meta', None), 'abstract', False) or 
            name == 'TypedModel'):
            return cls

        # Check if this inherits from a TypedModel
        typed_base = mcs._find_typed_base(bases)
        if typed_base:
            mcs._setup_sti_subclass(cls, typed_base)
        elif mcs._has_type_field(cls):
            # This has a TypeField, making it a typed base
            mcs._setup_sti_base(cls)

        return cls

    @classmethod
    def _find_typed_base(mcs, bases: tuple) -> Optional[Type[T]]:
        """Find a TypedModel base class."""
        for base in bases:
            if (hasattr(base, '__name__') and 
                hasattr(base, '_meta') and
                (getattr(base._meta, 'is_sti_base', False) or
                 mcs._has_type_field(base))):
                return base
        return None

    @classmethod
    def _has_type_field(mcs, cls: Type) -> bool:
        """Check if a class has a TypeField."""
        if not hasattr(cls, '_meta'):
            return False
        
        try:
            for field in cls._meta.get_fields():
                if isinstance(field, TypeField):
                    return True
        except:
            # Fallback to check declared fields
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name, None)
                if isinstance(attr, TypeField):
                    return True
        
        return False

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
        except:
            # Fallback if get_fields() fails
            type_field_name = "model_type"
        
        if type_field_name:
            cls._meta.type_field_name = type_field_name
            cls._meta.typed_models = {cls.__name__: cls}
        
        # Set up manager
        cls.objects = TypedModelManager()

    @classmethod
    def _setup_sti_subclass(mcs, cls: Type[T], base: Type[T]) -> None:
        """Set up an STI subclass using proxy approach."""
        cls._meta.is_sti_subclass = True
        cls._meta.sti_base_model = base
        
        # Use proxy approach - share table but not true proxy
        cls._meta.db_table = base._meta.db_table
        
        # Register with base model
        if hasattr(base._meta, 'typed_models'):
            base._meta.typed_models[cls.__name__] = cls
        
        # Share type field name
        if hasattr(base._meta, 'type_field_name'):
            cls._meta.type_field_name = base._meta.type_field_name
        
        # Set up manager
        cls.objects = TypedModelManager()




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
