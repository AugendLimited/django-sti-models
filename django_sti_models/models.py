"""
Core TypedModel implementation with robust Single Table Inheritance.

This implementation provides true STI where all subclasses share a single database table,
differentiated only by a type field. Key features:
- Automatic table sharing enforcement
- Type-aware querying
- Proper field inheritance
- Migration-safe design
"""

import threading
import weakref
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.manager import Manager
from django.db.models.options import Options
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

# Thread-safe registry for STI models
_sti_registry_lock = threading.RLock()
_sti_model_registry: Dict[str, Dict[str, Type]] = {}


class TypedModelManager(Manager[T]):
    """
    Enhanced manager for TypedModel with robust type-aware querying.
    
    Features:
    - Automatic type filtering for subclasses
    - Type validation on create/update operations
    - Performance optimizations for STI queries
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._typed_model_class: Optional[Type[T]] = None
        self._base_typed_model: Optional[Type[T]] = None

    def _set_typed_model_class(self, model_class: Type[T]) -> None:
        """Set the typed model class for this manager."""
        self._typed_model_class = model_class
        # Find the base STI model
        self._base_typed_model = self._find_base_sti_model(model_class)

    def _find_base_sti_model(self, model_class: Type[T]) -> Optional[Type[T]]:
        """Find the base STI model in the inheritance chain."""
        for base in model_class.__mro__:
            if (hasattr(base, '_meta') and 
                getattr(base._meta, 'is_sti_base', False)):
                return base
        return None

    def get_queryset(self) -> models.QuerySet[T]:
        """Get a queryset filtered by the correct type."""
        queryset = super().get_queryset()

        # Only filter if this is a subclass, not the base model
        if (self._typed_model_class is not None and 
            self._base_typed_model is not None and
            self._typed_model_class is not self._base_typed_model):
            
            type_field_name = self._get_type_field_name()
            if type_field_name:
                type_name = self._typed_model_class.__name__
                queryset = queryset.filter(**{type_field_name: type_name})

        return queryset

    def _get_type_field_name(self) -> Optional[str]:
        """Get the type field name, handling edge cases."""
        if self._base_typed_model:
            return getattr(self._base_typed_model._meta, 'type_field_name', None)
        elif self._typed_model_class:
            return getattr(self._typed_model_class._meta, 'type_field_name', None)
        return None

    def create(self, **kwargs: Any) -> T:
        """Create a new instance with the correct type."""
        if self._typed_model_class is not None:
            type_field_name = self._get_type_field_name()
            if type_field_name and type_field_name not in kwargs:
                kwargs[type_field_name] = self._typed_model_class.__name__

        return super().create(**kwargs)

    def get_or_create(
        self, defaults: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> tuple[T, bool]:
        """Get or create an instance with the correct type."""
        type_field_name = self._get_type_field_name()
        
        if self._typed_model_class is not None and type_field_name:
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
        type_field_name = self._get_type_field_name()
        
        if self._typed_model_class is not None and type_field_name:
            if type_field_name not in kwargs:
                kwargs[type_field_name] = self._typed_model_class.__name__

            if defaults is None:
                defaults = {}
            if type_field_name not in defaults:
                defaults[type_field_name] = self._typed_model_class.__name__

        return super().update_or_create(defaults=defaults, **kwargs)

    def get_for_type(self, type_name: str) -> models.QuerySet[T]:
        """Get instances of a specific type."""
        type_field_name = self._get_type_field_name()
        if type_field_name:
            return self.get_queryset().filter(**{type_field_name: type_name})
        return self.get_queryset().none()

    def exclude_types(self, *type_names: str) -> models.QuerySet[T]:
        """Exclude specific types from the queryset."""
        type_field_name = self._get_type_field_name()
        if type_field_name and type_names:
            return self.get_queryset().exclude(**{f"{type_field_name}__in": type_names})
        return self.get_queryset()


class TypedModelMeta(ModelBase):
    """
    Enhanced metaclass for TypedModel with robust STI support.

    Key improvements:
    1. Thread-safe type registration
    2. Proper table inheritance enforcement
    3. Migration-safe design
    4. Better error handling and validation
    5. Performance optimizations
    """

    def __new__(
        mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs: Any
    ) -> Type[T]:
        """Create a new typed model class with proper STI setup."""
        # Check for circular inheritance
        if name in [base.__name__ for base in bases if hasattr(base, "__name__")]:
            raise CircularInheritanceError(
                f"Circular inheritance detected for model '{name}'"
            )

        # Create the class first
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Skip processing for abstract models or during Django setup
        meta = namespace.get("Meta") or getattr(cls, "Meta", None)
        if (meta and getattr(meta, "abstract", False)) or not mcs._is_django_ready():
            return cls

        # Check if this is a TypedModel or inherits from one
        if mcs._is_typed_model(cls, bases):
            mcs._setup_typed_model(cls, bases)

        return cls

    @classmethod
    def _is_django_ready(mcs) -> bool:
        """Check if Django's app registry is ready."""
        try:
            from django.apps import apps
            apps.check_apps_ready()
            return True
        except Exception:
            return False

    @classmethod
    def _is_typed_model(mcs, cls: Type, bases: tuple) -> bool:
        """Check if this class should be treated as a typed model."""
        # Check if any base is TypedModel
        for base in bases:
            if (hasattr(base, '__name__') and 
                base.__name__ == 'TypedModel' and 
                hasattr(base, '_meta')):
                return True
            
            # Check if base has TypeField
            if (hasattr(base, '_meta') and 
                mcs._has_type_field(base)):
                return True
                
        # Check if this class itself has a TypeField
        return mcs._has_type_field(cls)

    @classmethod
    def _has_type_field(mcs, model_class: Type) -> bool:
        """Check if a model class has a TypeField."""
        if not hasattr(model_class, '_meta'):
            return False
            
        # Check declared fields
        for field in getattr(model_class._meta, 'fields', []):
            if isinstance(field, TypeField):
                return True
                
        # Check field map if available
        fields_map = getattr(model_class._meta, 'fields_map', {})
        for field in fields_map.values():
            if isinstance(field, TypeField):
                return True
                
        return False

    @classmethod
    def _setup_typed_model(mcs, cls: Type[T], bases: tuple) -> None:
        """Set up a typed model with proper STI configuration."""
        with _sti_registry_lock:
            # Find or establish the base STI model
            base_sti_model = mcs._find_base_sti_model(cls, bases)
            
            if base_sti_model is None:
                # This is the base STI model
                mcs._setup_base_sti_model(cls)
            else:
                # This is a subclass - set up STI inheritance
                mcs._setup_sti_subclass(cls, base_sti_model)

    @classmethod
    def _find_base_sti_model(mcs, cls: Type[T], bases: tuple) -> Optional[Type[T]]:
        """Find the base STI model in the inheritance chain."""
        for base in bases:
            if (hasattr(base, '_meta') and 
                getattr(base._meta, 'is_sti_base', False)):
                return base
                
            # Check if this base has a TypeField and is not abstract
            if (mcs._has_type_field(base) and 
                not getattr(getattr(base, 'Meta', None), 'abstract', False)):
                return base
                
        return None

    @classmethod
    def _setup_base_sti_model(mcs, cls: Type[T]) -> None:
        """Set up the base STI model."""
        # Mark as STI base
        cls._meta.is_sti_base = True
        
        # Find and register the type field
        type_field_name = mcs._find_type_field_name(cls)
        if type_field_name:
            cls._meta.type_field_name = type_field_name
            
            # Initialize type registry
            base_key = f"{cls._meta.app_label}.{cls.__name__}"
            _sti_model_registry[base_key] = {cls.__name__: cls}
            
            # Set up manager
            mcs._setup_manager(cls)
            
            # Store registry reference
            cls._meta.typed_models = _sti_model_registry[base_key]
        else:
            raise TypeFieldNotFoundError(
                f"No TypeField found in STI base model {cls.__name__}"
            )

    @classmethod
    def _setup_sti_subclass(mcs, cls: Type[T], base_sti_model: Type[T]) -> None:
        """Set up an STI subclass."""
        # Mark as STI subclass
        cls._meta.is_sti_subclass = True
        cls._meta.sti_base_model = base_sti_model
        
        # Force table inheritance
        mcs._force_table_inheritance(cls, base_sti_model)
        
        # Register the type
        mcs._register_sti_type(cls, base_sti_model)
        
        # Set up manager
        mcs._setup_manager(cls)

    @classmethod
    def _force_table_inheritance(mcs, cls: Type[T], base_sti_model: Type[T]) -> None:
        """Force the subclass to use the base model's table."""
        # Set the same db_table as the base model
        base_table_name = base_sti_model._meta.db_table
        cls._meta.db_table = base_table_name
        
        # Ensure the model is managed (not unmanaged)
        cls._meta.managed = True
        
        # Mark as STI model sharing a table
        cls._meta.sti_table_shared = True
        cls._meta.sti_shared_table_name = base_table_name
        
        # Store reference to the base model for later use
        cls._meta.sti_base_model_ref = base_sti_model

    @classmethod
    def _register_sti_type(mcs, cls: Type[T], base_sti_model: Type[T]) -> None:
        """Register the STI type in the base model's registry."""
        base_key = f"{base_sti_model._meta.app_label}.{base_sti_model.__name__}"
        
        if base_key not in _sti_model_registry:
            _sti_model_registry[base_key] = {}
            
        _sti_model_registry[base_key][cls.__name__] = cls
        
        # Update base model's typed_models reference
        base_sti_model._meta.typed_models = _sti_model_registry[base_key]
        
        # Share the type field name
        cls._meta.type_field_name = base_sti_model._meta.type_field_name

    @classmethod
    def _find_type_field_name(mcs, cls: Type[T]) -> Optional[str]:
        """Find the name of the TypeField in the model."""
        for field in cls._meta.fields:
            if isinstance(field, TypeField):
                return field.name
        return None

    @classmethod
    def _setup_manager(mcs, cls: Type[T]) -> None:
        """Set up the typed model manager."""
        manager = TypedModelManager()
        manager._set_typed_model_class(cls)
        
        # Replace the default manager
        cls.objects = manager
        
        # Set as default manager in meta
        if not hasattr(cls._meta, "default_manager"):
            cls._meta.default_manager = manager




class TypedModel(models.Model, metaclass=TypedModelMeta):
    """
    Enhanced base class for Single Table Inheritance (STI) models.

    This provides robust STI implementation with:
    - Automatic type field management
    - Type-aware querying and instantiation
    - Proper polymorphic behavior
    - Migration-safe design
    - Thread-safe type registration
    """

    # Default type field - subclasses can override the field name
    model_type = TypeField()

    class Meta:
        abstract = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the typed model with automatic type setting."""
        # Automatically set the type field if not provided
        type_field_name = self.get_type_field_name()
        if type_field_name and type_field_name not in kwargs:
            kwargs[type_field_name] = self.__class__.__name__

        super().__init__(*args, **kwargs)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the model, ensuring the type field is correctly set."""
        # Ensure the type field is set to the current class name
        type_field_name = self.get_type_field_name()
        if type_field_name:
            current_type = getattr(self, type_field_name, None)
            expected_type = self.__class__.__name__
            
            if not current_type or current_type != expected_type:
                setattr(self, type_field_name, expected_type)

        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Validate the model, including type field consistency."""
        super().clean()
        
        # Validate type field
        type_field_name = self.get_type_field_name()
        if type_field_name:
            type_value = getattr(self, type_field_name, None)
            expected_type = self.__class__.__name__
            
            if type_value and type_value != expected_type:
                raise ValidationError({
                    type_field_name: f"Type field must be '{expected_type}' for {self.__class__.__name__} instances"
                })

    @classmethod
    def get_type_class(cls, type_name: str) -> Optional[Type[T]]:
        """Get the model class for a given type name."""
        base_model = cls.get_sti_base_model()
        if base_model and hasattr(base_model._meta, "typed_models"):
            return base_model._meta.typed_models.get(type_name)
        return None

    @classmethod
    def get_all_types(cls) -> Dict[str, Type[T]]:
        """Get all registered types for this STI hierarchy."""
        base_model = cls.get_sti_base_model()
        if base_model and hasattr(base_model._meta, "typed_models"):
            return base_model._meta.typed_models.copy()
        return {}

    @classmethod
    def get_sti_base_model(cls) -> Optional[Type[T]]:
        """Get the base STI model for this class hierarchy."""
        # Check if this is the base model
        if getattr(cls._meta, 'is_sti_base', False):
            return cls
            
        # Check if we have a reference to the base model
        if hasattr(cls._meta, 'sti_base_model'):
            return cls._meta.sti_base_model
            
        # Search the MRO for the base model
        for base in cls.__mro__:
            if (hasattr(base, '_meta') and 
                getattr(base._meta, 'is_sti_base', False)):
                return base
                
        return None

    def get_real_instance(self) -> T:
        """Get the correctly typed instance of this object."""
        type_field_name = self.get_type_field_name()
        if not type_field_name:
            return self
            
        current_type = getattr(self, type_field_name, None)
        if not current_type:
            return self

        # If already the correct type, return self
        if current_type == self.__class__.__name__:
            return self

        # Get the correct class and return an instance of it
        type_class = self.get_type_class(current_type)
        if type_class is None or type_class is self.__class__:
            return self

        # Create an instance of the correct type with the same data
        try:
            return type_class.objects.get(pk=self.pk)
        except ObjectDoesNotExist:
            return self

    @classmethod
    def from_db(cls, db: str, field_names: List[str], values: List[Any]) -> T:
        """Create an instance from database values with automatic type conversion."""
        # Create the instance normally first
        instance = super().from_db(db, field_names, values)

        # Try to convert to the correct type if needed
        type_field_name = cls.get_type_field_name()
        if type_field_name:
            # Find the type field value in the data
            type_value = None
            try:
                type_field_index = field_names.index(type_field_name)
                type_value = values[type_field_index]
            except (ValueError, IndexError):
                pass

            # If we have a type value and it's different from current class
            if type_value and type_value != cls.__name__:
                type_class = cls.get_type_class(type_value)
                if type_class and type_class is not cls:
                    # Create an instance of the correct type
                    return type_class.from_db(db, field_names, values)

        return instance

    @classmethod
    def get_type_field_name(cls) -> str:
        """Get the name of the type field for this model hierarchy."""
        # Try to get from meta first
        if hasattr(cls._meta, "type_field_name"):
            return cls._meta.type_field_name
            
        # Try to get from base model
        base_model = cls.get_sti_base_model()
        if base_model and hasattr(base_model._meta, "type_field_name"):
            return base_model._meta.type_field_name
            
        # Default fallback
        return "model_type"

    @classmethod
    def is_sti_model(cls) -> bool:
        """Check if this is part of an STI hierarchy."""
        return (getattr(cls._meta, 'is_sti_base', False) or 
                getattr(cls._meta, 'is_sti_subclass', False))

    @classmethod
    def create_typed_instance(cls, type_name: str, **kwargs: Any) -> T:
        """Create an instance of a specific type."""
        type_class = cls.get_type_class(type_name)
        if type_class is None:
            raise STIException(f"Unknown type '{type_name}' for {cls.__name__}")
            
        return type_class.objects.create(**kwargs)

    def get_type_display_name(self) -> str:
        """Get a human-readable display name for this instance's type."""
        type_field_name = self.get_type_field_name()
        if type_field_name:
            type_value = getattr(self, type_field_name, None)
            if type_value:
                return type_value.replace('_', ' ').title()
        return self.__class__.__name__

    @classmethod
    def validate_sti_setup(cls) -> List[str]:
        """Validate the STI setup for this model hierarchy."""
        errors = []
        
        # Check if this is an STI model
        if not cls.is_sti_model():
            errors.append(f"{cls.__name__} is not part of an STI hierarchy")
            return errors
            
        # Check type field
        type_field_name = cls.get_type_field_name()
        if not type_field_name:
            errors.append(f"No type field found for {cls.__name__}")
            return errors
            
        # Check if type field exists
        try:
            field = cls._meta.get_field(type_field_name)
            if not isinstance(field, TypeField):
                errors.append(f"Type field '{type_field_name}' is not a TypeField")
        except Exception as e:
            errors.append(f"Type field '{type_field_name}' not found: {e}")
            
        # Check type registration
        all_types = cls.get_all_types()
        if cls.__name__ not in all_types:
            errors.append(f"Type '{cls.__name__}' is not registered")
            
        # Check table sharing for STI subclasses
        if getattr(cls._meta, 'is_sti_subclass', False):
            base_model = cls.get_sti_base_model()
            if base_model:
                base_table = base_model._meta.db_table
                subclass_table = cls._meta.db_table
                if base_table != subclass_table:
                    errors.append(f"STI subclass {cls.__name__} table '{subclass_table}' doesn't match base table '{base_table}'")
            
        return errors

    @classmethod
    def get_sti_table_info(cls) -> Dict[str, Any]:
        """Get detailed information about STI table configuration."""
        info = {
            'model_name': cls.__name__,
            'is_sti_model': cls.is_sti_model(),
            'is_sti_base': getattr(cls._meta, 'is_sti_base', False),
            'is_sti_subclass': getattr(cls._meta, 'is_sti_subclass', False),
            'db_table': cls._meta.db_table,
            'type_field_name': cls.get_type_field_name(),
        }
        
        # Add base model info if this is a subclass
        if info['is_sti_subclass']:
            base_model = cls.get_sti_base_model()
            if base_model:
                info['base_model'] = base_model.__name__
                info['base_table'] = base_model._meta.db_table
                info['table_shared'] = info['db_table'] == info['base_table']
        
        # Add registered types if this is STI base
        if info['is_sti_base'] or info['is_sti_subclass']:
            info['registered_types'] = list(cls.get_all_types().keys())
            
        return info
