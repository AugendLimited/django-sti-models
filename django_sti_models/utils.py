"""
Utility functions for Django STI Models.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union

from django.db import models
from django.db.models import QuerySet

from .exceptions import STIException
from .models import TypedModel


def get_typed_queryset(
    base_model: Type[TypedModel], type_names: Optional[List[str]] = None
) -> QuerySet[TypedModel]:
    """
    Get a queryset for typed models, optionally filtered by type names.

    Args:
        base_model: The base typed model class
        type_names: Optional list of type names to filter by

    Returns:
        A queryset filtered by the specified types
    """
    queryset = base_model.objects.all()

    if type_names:
        type_field_name = base_model._meta.type_field_name
        queryset = queryset.filter(**{f"{type_field_name}__in": type_names})

    return queryset


def create_typed_instance(
    base_model: Type[TypedModel], type_name: str, **kwargs: Any
) -> TypedModel:
    """
    Create a typed instance by type name.

    Args:
        base_model: The base typed model class
        type_name: The name of the type to create
        **kwargs: Additional arguments to pass to the model constructor

    Returns:
        A new instance of the specified type

    Raises:
        STIException: If the type is not registered
    """
    type_class = base_model.get_type_class(type_name)
    if type_class is None:
        raise STIException(
            f"Type '{type_name}' is not registered for {base_model.__name__}"
        )

    return type_class.objects.create(**kwargs)


def get_type_hierarchy(base_model: Type[TypedModel]) -> Dict[str, List[str]]:
    """
    Get the type hierarchy for a base model.

    Args:
        base_model: The base typed model class

    Returns:
        A dictionary mapping type names to their parent types
    """
    hierarchy = {}
    registered_types = base_model.get_all_types()

    for type_name, type_class in registered_types.items():
        parents = []
        for base in type_class.__mro__[1:]:  # Skip the class itself
            if base in registered_types.values():
                parents.append(base.__name__)
        hierarchy[type_name] = parents

    return hierarchy


def validate_type_registration(base_model: Type[TypedModel]) -> List[str]:
    """
    Validate the type registration for a base model.

    Args:
        base_model: The base typed model class

    Returns:
        A list of validation error messages
    """
    errors = []
    registered_types = base_model.get_all_types()

    if not registered_types:
        errors.append(f"No types registered for {base_model.__name__}")

    for type_name, type_class in registered_types.items():
        # Check if the type name matches the class name
        if type_class.__name__ != type_name:
            errors.append(
                f"Type name '{type_name}' doesn't match class name '{type_class.__name__}'"
            )

        # Check if the type has the required type field
        type_field_name = base_model.get_type_field_name()
        if (
            not hasattr(type_class._meta, "fields_map")
            or type_field_name not in type_class._meta.fields_map
        ):
            errors.append(
                f"Type '{type_name}' is missing the required type field '{type_field_name}'"
            )

    return errors


def get_type_field_value(instance: TypedModel) -> Optional[str]:
    """
    Get the type field value for an instance.

    Args:
        instance: A typed model instance

    Returns:
        The type field value
    """
    type_field_name = instance.get_type_field_name()
    return getattr(instance, type_field_name, None)


def is_typed_instance(instance: Any) -> bool:
    """
    Check if an instance is a typed model instance.

    Args:
        instance: Any object

    Returns:
        True if the instance is a typed model instance
    """
    return isinstance(instance, TypedModel) and hasattr(instance, "type")


@lru_cache(maxsize=128)
def get_typed_model_classes(base_model: Type[TypedModel]) -> Set[Type[TypedModel]]:
    """
    Get all typed model classes for a base model (cached).

    Args:
        base_model: The base typed model class

    Returns:
        A set of all typed model classes
    """
    return set(base_model.get_all_types().values())


def filter_by_type(
    queryset: QuerySet[TypedModel], type_names: Union[str, List[str]]
) -> QuerySet[TypedModel]:
    """
    Filter a queryset by type names.

    Args:
        queryset: A queryset of typed models
        type_names: A single type name or list of type names

    Returns:
        A filtered queryset
    """
    if isinstance(type_names, str):
        type_names = [type_names]

    if not type_names:
        return queryset

    model_class = queryset.model
    type_field_name = model_class.get_type_field_name()
    return queryset.filter(**{f"{type_field_name}__in": type_names})


def get_type_statistics(base_model: Type[TypedModel]) -> Dict[str, int]:
    """
    Get statistics about the distribution of types in the database.

    Args:
        base_model: The base typed model class

    Returns:
        A dictionary mapping type names to their counts
    """
    from django.db.models import Count

    type_field_name = base_model.get_type_field_name()
    stats = (
        base_model.objects.values(type_field_name)
        .annotate(count=Count(type_field_name))
        .order_by(type_field_name)
    )

    return {item[type_field_name]: item["count"] for item in stats}


def migrate_type_field(
    base_model: Type[TypedModel], old_type_field: str, new_type_field: str
) -> int:
    """
    Migrate data from an old type field to a new type field.

    Args:
        base_model: The base typed model class
        old_type_field: The name of the old type field
        new_type_field: The name of the new type field

    Returns:
        The number of records updated
    """
    updated_count = 0

    for instance in base_model.objects.all():
        if hasattr(instance, old_type_field):
            old_value = getattr(instance, old_type_field)
            if old_value:
                setattr(instance, new_type_field, old_value)
                instance.save(update_fields=[new_type_field])
                updated_count += 1

    return updated_count


def validate_type_consistency(base_model: Type[TypedModel]) -> List[str]:
    """
    Validate that all instances have consistent type field values.

    Args:
        base_model: The base typed model class

    Returns:
        A list of validation error messages
    """
    errors = []
    type_field_name = base_model.get_type_field_name()
    registered_types = set(base_model.get_all_types().keys())

    # Check for instances with unregistered types
    invalid_types = (
        base_model.objects.exclude(**{f"{type_field_name}__in": list(registered_types)})
        .values_list(type_field_name, flat=True)
        .distinct()
    )

    for invalid_type in invalid_types:
        if invalid_type:
            errors.append(f"Found instances with unregistered type: {invalid_type}")

    # Check for instances with null type fields
    null_count = base_model.objects.filter(**{type_field_name: None}).count()
    if null_count > 0:
        errors.append(f"Found {null_count} instances with null type field")

    return errors
