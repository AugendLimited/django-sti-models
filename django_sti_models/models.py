"""
Simple and robust Single Table Inheritance for Django.

This implementation provides clean STI with:
- Automatic table sharing for subclasses
- Type-aware querying and management
- Support for both concrete and abstract base classes
- Uses Django's ContentType system for reliable type tracking
- Forces proxy model behavior for subclasses
"""

from typing import Any, Dict, Optional, Type, TypeVar, cast

from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.fields import Field
from django.db.models.manager import Manager

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
            # Use ContentType to filter by the actual model class
            from django.contrib.contenttypes.models import ContentType

            content_type = ContentType.objects.get_for_model(self.model_class)
            field_name = self.model_class.get_content_type_field_name()
            queryset = queryset.filter(**{field_name: content_type})

        return queryset

    def create(self, **kwargs: Any) -> T:
        """Create a new instance with the correct type."""
        # Set the ContentType automatically
        field_name = self.model_class.get_content_type_field_name()
        if field_name not in kwargs and self.model_class:
            from django.contrib.contenttypes.models import ContentType

            content_type = ContentType.objects.get_for_model(self.model_class)
            kwargs[field_name] = content_type

        return super().create(**kwargs)


class TypedModelMeta(ModelBase):
    """Metaclass for STI models using Django's ContentType system."""

    def __new__(
        mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs: Any
    ) -> Type[T]:
        """Create a new typed model class."""

        # Skip TypedModel itself
        if name == "TypedModel":
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            cls._meta.fields_from_subclasses = {}
            return cls

        # Look for a non-proxy base class that is a subclass of TypedModel
        mro = list(bases)
        base_class = None
        while mro:
            base_class = mro.pop(-1)
            if issubclass(base_class, TypedModel) and base_class is not TypedModel:
                if base_class._meta.proxy or base_class._meta.abstract:
                    # continue up the mro looking for non-proxy base classes
                    mro.extend(base_class.__bases__)
                else:
                    break
        else:
            base_class = None

        if base_class:
            # Enforce that subclasses are proxy models
            Meta = namespace.get("Meta", type("Meta", (), {}))
            if getattr(Meta, "proxy", False):
                # If user has specified proxy=True explicitly, treat as ordinary proxy
                return cast(
                    Type[T], super().__new__(mcs, name, bases, namespace, **kwargs)
                )
            Meta.proxy = True

            # Extract declared fields from subclass
            declared_fields = dict(
                (field_name, field_obj)
                for field_name, field_obj in list(namespace.items())
                if isinstance(field_obj, Field)
            )

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
                    existing_field = base_class._meta.get_field(field_name)
                    # Check if it's exactly the same field
                    if existing_field.deconstruct()[1:] != field.deconstruct()[1:]:
                        raise ValueError(
                            f"Field '{field_name}' from '{name}' conflicts with "
                            f"existing field on '{base_class.__name__}'"
                        )
                except FieldDoesNotExist:
                    # Field doesn't exist, add it to base class
                    field.contribute_to_class(base_class, field_name)

                # Remove field from subclass namespace
                namespace.pop(field_name)

            # Track fields added from subclasses
            if hasattr(base_class._meta, "fields_from_subclasses"):
                base_class._meta.fields_from_subclasses.update(declared_fields)

            # Set app_label to the same as the base class
            if not hasattr(Meta, "app_label"):
                if hasattr(getattr(base_class, "_meta", None), "app_label"):
                    Meta.app_label = base_class._meta.app_label

            namespace["Meta"] = Meta

        namespace["base_class"] = base_class

        # Create the class
        cls = cast(Type[T], super().__new__(mcs, name, bases, namespace, **kwargs))

        cls._meta.fields_from_subclasses = {}

        if base_class:
            # This is an STI subclass
            cls._meta.is_sti_subclass = True
            cls._meta.sti_base_model = base_class

            # Register with base model
            if hasattr(base_class._meta, "typed_models"):
                base_class._meta.typed_models[cls.__name__] = cls

            # Set up manager
            manager = TypedModelManager()
            manager.contribute_to_class(cls, "objects")
            cls.objects = manager

        elif not cls._meta.abstract:
            # This is the base class
            cls._meta.is_sti_base = True
            cls._meta.typed_models = {cls.__name__: cls}

            # Add the ContentType field dynamically
            field_name = cls.get_content_type_field_name()
            content_type_field = models.ForeignKey(
                "contenttypes.ContentType",
                on_delete=models.CASCADE,
                null=True,
                blank=True,
                editable=False,
                verbose_name="polymorphic type",
                related_name=f"polymorphic_%(app_label)s.%(class)s_set+",
            )
            content_type_field.contribute_to_class(cls, field_name)

            # Set up manager
            manager = TypedModelManager()
            manager.contribute_to_class(cls, "objects")
            cls.objects = manager

        return cls


class TypedModel(models.Model, metaclass=TypedModelMeta):
    """Base class for Single Table Inheritance (STI) models using ContentType."""

    class Meta:
        abstract = True

    @classmethod
    def get_content_type_field_name(cls) -> str:
        """Get the name of the ContentType field for this model."""
        # Check if a custom field name is defined in Meta
        if hasattr(cls._meta, "type_field"):
            return cls._meta.type_field
        return "polymorphic_ctype"

    def _get_content_type_field(self):
        """Get the ContentType field instance."""
        field_name = self.get_content_type_field_name()
        return getattr(self, field_name)

    def _set_content_type_field(self, value):
        """Set the ContentType field value."""
        field_name = self.get_content_type_field_name()
        setattr(self, field_name, value)

    def _get_content_type_field_id(self):
        """Get the ContentType field ID."""
        field_name = self.get_content_type_field_name()
        return getattr(self, f"{field_name}_id")

    def _set_content_type_field_id(self, value):
        """Set the ContentType field ID."""
        field_name = self.get_content_type_field_name()
        setattr(self, f"{field_name}_id", value)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the model, ensuring the ContentType is set."""
        # Set the ContentType to the current class if not already set
        if not self._get_content_type_field_id():
            from django.contrib.contenttypes.models import ContentType

            self._set_content_type_field(
                ContentType.objects.get_for_model(self.__class__)
            )

        super().save(*args, **kwargs)

    def get_real_instance_class(self) -> Optional[Type[T]]:
        """Get the real class of this instance."""
        if not self._get_content_type_field_id():
            return None

        try:
            return self._get_content_type_field().model_class()
        except Exception:
            return None

    @classmethod
    def get_type_class(cls, type_name: str) -> Optional[Type[T]]:
        """Get the model class for a given type name."""
        try:
            from django.contrib.contenttypes.models import ContentType

            content_type = ContentType.objects.get(model=type_name.lower())
            return content_type.model_class()
        except ContentType.DoesNotExist:
            return None
