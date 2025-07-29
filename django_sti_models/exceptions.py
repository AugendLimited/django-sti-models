"""
Custom exceptions for Django STI Models.
"""


class STIException(Exception):
    """Base exception for Django STI Models."""
    pass


class InvalidTypeError(STIException):
    """Raised when an invalid type is provided."""
    pass


class TypeFieldNotFoundError(STIException):
    """Raised when the type field is not found on the model."""
    pass


class CircularInheritanceError(STIException):
    """Raised when circular inheritance is detected."""
    pass


class TypeRegistrationError(STIException):
    """Raised when there's an error registering a type."""
    pass 