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
    """Metaclass for STI models using Django's proxy model approach."""

    def __new__(
        mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs: Any
    ) -> Type[T]:
        """Create a new typed model class."""
        
        print(f"\n🔍 DEBUG: Creating class '{name}'")
        print(f"   Bases: {[b.__name__ for b in bases]}")
        
        # Skip TypedModel itself
        if name == 'TypedModel':
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            cls._meta.fields_from_subclasses = {}
            print(f"   ✅ Created TypedModel base class")
            return cls

        # Skip abstract models
        Meta = namespace.get('Meta')
        if Meta and getattr(Meta, 'abstract', False):
            print(f"   ⏭️ Skipping abstract model '{name}'")
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        # Check if this inherits from a TypedModel
        typed_base = mcs._find_typed_base(bases)
        print(f"   🔎 typed_base found: {typed_base.__name__ if typed_base else 'None'}")

        if typed_base:
            print(f"   🎯 '{name}' is STI SUBCLASS of '{typed_base.__name__}'")

            # This is an STI subclass - force proxy=True BEFORE class creation
            Meta = namespace.get('Meta', type('Meta', (), {}))
            if hasattr(Meta, 'proxy') and getattr(Meta, 'proxy', False):
                # User explicitly set proxy=True, treat as regular proxy
                print(f"   ⚠️ User set proxy=True explicitly for '{name}' - treating as regular proxy")
                return super().__new__(mcs, name, bases, namespace, **kwargs)
            
            # Extract declared fields from subclass
            from django.db.models.fields import Field
            from django.core.exceptions import FieldError
            
            declared_fields = dict(
                (field_name, field_obj)
                for field_name, field_obj in list(namespace.items())
                if isinstance(field_obj, Field)
            )
            print(f"   📝 Fields found on '{name}': {list(declared_fields.keys())}")
            
            # Validate and move fields to base class
            for field_name, field in list(declared_fields.items()):
                # Fields on STI subclasses must be nullable or have defaults
                if not (field.many_to_many or field.null or field.has_default()):
                    raise FieldError(
                        f"All fields defined on STI subclasses must be nullable "
                        f"or have a default value. For {name}.{field_name}, either:\n"
                        f"  - Add null=True (allows NULL in database)\n"
                        f"  - Add default='...' (provides default value)\n"
                        f"This prevents Multi-Table Inheritance (MTI) and ensures "
                        f"true Single Table Inheritance (STI)."
                    )
                
                # Check if field already exists on base class
                try:
                    existing_field = typed_base._meta.get_field(field_name)
                    # Check if it's exactly the same field
                    if existing_field.deconstruct()[1:] != field.deconstruct()[1:]:
                        raise ValueError(
                            f"Field '{field_name}' from '{name}' conflicts with "
                            f"existing field on '{typed_base.__name__}'"
                        )
                except:
                    # Field doesn't exist, add it to base class
                    print(f"   🔄 Moving field '{field_name}' from '{name}' to '{typed_base.__name__}'")
                    field.contribute_to_class(typed_base, field_name)
                
                # Remove field from subclass namespace
                print(f"   🗑️ Removing field '{field_name}' from '{name}' namespace")
                namespace.pop(field_name)
            
            # Track fields added from subclasses
            if hasattr(typed_base._meta, 'fields_from_subclasses'):
                typed_base._meta.fields_from_subclasses.update(declared_fields)
            
            # Force proxy=True for STI behavior
            print(f"   🎭 Setting proxy=True for '{name}'")
            Meta.proxy = True
            namespace['Meta'] = Meta
            
            # Create the class
            print(f"   🏗️ Creating STI subclass '{name}' with proxy=True")
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            cls._meta.fields_from_subclasses = {}
            print(f"   ✅ Created '{name}', proxy status: {getattr(cls._meta, 'proxy', False)}")
            mcs._setup_sti_subclass(cls, typed_base)
        else:
            # Create the class normally  
            print(f"   🏗️ Creating normal class '{name}' (not STI subclass)")
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            cls._meta.fields_from_subclasses = {}
            if mcs._has_type_field(cls):
                # This has a TypeField, making it a typed base
                print(f"   🎯 '{name}' has TypeField - setting up as STI BASE")
                mcs._setup_sti_base(cls)
            else:
                print(f"   ❌ '{name}' has no TypeField")

        return cls

    @classmethod
    def _find_typed_base(mcs, bases: tuple) -> Optional[Type[T]]:
        """Find a concrete STI base class (not the abstract TypedModel)."""
        print(f"   🔍 _find_typed_base checking: {[b.__name__ for b in bases]}")
        for base in bases:
            if hasattr(base, '__name__') and hasattr(base, '_meta'):
                print(f"     📋 Checking base: {base.__name__}")
                
                # Skip the abstract TypedModel itself
                if base.__name__ == 'TypedModel':
                    print(f"       ⏭️ Skipping abstract TypedModel")
                    continue
                    
                is_sti_base = getattr(base._meta, 'is_sti_base', False)
                has_type_field = mcs._has_type_field(base)
                is_abstract = getattr(base._meta, 'abstract', False)
                
                print(f"       📊 {base.__name__}: is_sti_base={is_sti_base}, has_type_field={has_type_field}, abstract={is_abstract}")
                
                # Only concrete STI bases (either already marked or having TypeField)
                if (is_sti_base or has_type_field) and not is_abstract:
                    print(f"       ✅ Found typed base: {base.__name__}")
                    return base
                else:
                    print(f"       ❌ {base.__name__} not qualified as STI base")
        print(f"   ❌ No concrete STI base found")
        return None

    @classmethod
    def _has_type_field(mcs, cls: Type) -> bool:
        """Check if a class has a TypeField."""
        print(f"       🔍 _has_type_field checking {cls.__name__}")
        if not hasattr(cls, '_meta'):
            print(f"       ❌ {cls.__name__} has no _meta")
            return False
        
        try:
            fields = cls._meta.get_fields()
            print(f"       📝 {cls.__name__} fields via get_fields(): {[f.name for f in fields]}")
            for field in fields:
                if isinstance(field, TypeField):
                    print(f"       ✅ Found TypeField: {field.name}")
                    return True
        except Exception as e:
            print(f"       ⚠️ get_fields() failed for {cls.__name__}: {e}")
            # Fallback to check declared fields
            print(f"       🔄 Fallback: checking dir({cls.__name__})")
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name, None)
                if isinstance(attr, TypeField):
                    print(f"       ✅ Found TypeField via dir(): {attr_name}")
                    return True
        
        print(f"       ❌ No TypeField found in {cls.__name__}")
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
        """Set up an STI subclass using Django's proxy model approach."""
        cls._meta.is_sti_subclass = True
        cls._meta.sti_base_model = base
        
        # Note: proxy=True is already set in __new__ before class creation
        # This ensures Django creates no separate table for the subclass
        
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
