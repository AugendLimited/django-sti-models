"""
Tests for TypedModel implementation.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from django_sti_models import TypedModel, TypeField
from django_sti_models.exceptions import (
    CircularInheritanceError,
    STIException,
    TypeFieldNotFoundError,
)


class Animal(TypedModel):
    """Base animal model for testing."""

    name = models.CharField(max_length=100)
    age = models.IntegerField()
    animal_type = TypeField()  # More descriptive than 'type'

    class Meta:
        abstract = True


class Dog(Animal):
    """Dog subtype for testing."""

    breed = models.CharField(max_length=50)

    def bark(self):
        return f"{self.name} says woof!"


class Cat(Animal):
    """Cat subtype for testing."""

    color = models.CharField(max_length=30)

    def meow(self):
        return f"{self.name} says meow!"


class Bird(Animal):
    """Bird subtype for testing."""

    wingspan = models.FloatField()

    def fly(self):
        return f"{self.name} is flying!"


class Vehicle(TypedModel):
    """Vehicle model with custom type field name."""

    name = models.CharField(max_length=100)
    vehicle_kind = TypeField()  # Custom field name

    class Meta:
        abstract = True


class Car(Vehicle):
    """Car subtype for testing."""

    doors = models.IntegerField()


class Motorcycle(Vehicle):
    """Motorcycle subtype for testing."""

    engine_size = models.FloatField()


class TypedModelTestCase(TestCase):
    """Test case for TypedModel functionality."""

    def setUp(self):
        """Set up test data."""
        self.dog = Dog.objects.create(name="Rex", age=3, breed="Golden Retriever")
        self.cat = Cat.objects.create(name="Whiskers", age=2, color="Orange")
        self.bird = Bird.objects.create(name="Tweety", age=1, wingspan=12.5)

    def test_type_field_automatically_set(self):
        """Test that the type field is automatically set."""
        self.assertEqual(self.dog.animal_type, "Dog")
        self.assertEqual(self.cat.animal_type, "Cat")
        self.assertEqual(self.bird.animal_type, "Bird")

    def test_type_registration(self):
        """Test that types are properly registered."""
        registered_types = Animal.get_all_types()
        self.assertIn("Dog", registered_types)
        self.assertIn("Cat", registered_types)
        self.assertIn("Bird", registered_types)
        self.assertEqual(registered_types["Dog"], Dog)
        self.assertEqual(registered_types["Cat"], Cat)
        self.assertEqual(registered_types["Bird"], Bird)

    def test_get_type_class(self):
        """Test getting type class by name."""
        self.assertEqual(Animal.get_type_class("Dog"), Dog)
        self.assertEqual(Animal.get_type_class("Cat"), Cat)
        self.assertEqual(Animal.get_type_class("Bird"), Bird)
        self.assertIsNone(Animal.get_type_class("NonExistent"))

    def test_queryset_filtering(self):
        """Test that querysets are properly filtered by type."""
        dogs = Dog.objects.all()
        self.assertEqual(dogs.count(), 1)
        self.assertEqual(dogs.first(), self.dog)

        cats = Cat.objects.all()
        self.assertEqual(cats.count(), 1)
        self.assertEqual(cats.first(), self.cat)

        birds = Bird.objects.all()
        self.assertEqual(birds.count(), 1)
        self.assertEqual(birds.first(), self.bird)

    def test_base_model_queryset(self):
        """Test that base model queryset returns all types."""
        all_animals = Animal.objects.all()
        self.assertEqual(all_animals.count(), 3)

        # Check that we get the correct types
        animal_types = [animal.animal_type for animal in all_animals]
        self.assertIn("Dog", animal_types)
        self.assertIn("Cat", animal_types)
        self.assertIn("Bird", animal_types)

    def test_get_real_instance(self):
        """Test getting the real instance of the correct type."""
        # Get an animal from the base queryset
        animal = Animal.objects.filter(animal_type="Dog").first()
        real_animal = animal.get_real_instance()

        self.assertIsInstance(real_animal, Dog)
        self.assertEqual(real_animal.pk, self.dog.pk)
        self.assertEqual(real_animal.name, self.dog.name)

    def test_custom_type_field_name(self):
        """Test models with custom type field names."""
        car = Car.objects.create(name="Tesla", doors=4)
        motorcycle = Motorcycle.objects.create(name="Harley", engine_size=1200.0)

        self.assertEqual(car.vehicle_kind, "Car")
        self.assertEqual(motorcycle.vehicle_kind, "Motorcycle")

        # Test queryset filtering
        cars = Car.objects.all()
        self.assertEqual(cars.count(), 1)
        self.assertEqual(cars.first(), car)

        motorcycles = Motorcycle.objects.all()
        self.assertEqual(motorcycles.count(), 1)
        self.assertEqual(motorcycles.first(), motorcycle)

    def test_type_field_validation(self):
        """Test type field validation."""
        # Try to create an animal with an invalid type
        with self.assertRaises(ValidationError):
            invalid_animal = Animal(name="Invalid", age=1, animal_type="InvalidType")
            invalid_animal.full_clean()

    def test_circular_inheritance_detection(self):
        """Test detection of circular inheritance."""
        # This should raise an error if we try to create a class with the same name
        # as one of its bases
        with self.assertRaises(CircularInheritanceError):

            class Dog(Dog):  # This would create circular inheritance
                pass

    def test_abstract_model_handling(self):
        """Test that abstract models are handled correctly."""

        # Abstract models should not be processed for type registration
        class AbstractAnimal(TypedModel):
            name = models.CharField(max_length=100)

            class Meta:
                abstract = True

        # This should not raise any errors
        self.assertTrue(hasattr(AbstractAnimal, "_meta"))

    def test_manager_create_method(self):
        """Test that the manager's create method sets the type correctly."""
        new_dog = Dog.objects.create(name="Buddy", age=5, breed="Labrador")
        self.assertEqual(new_dog.animal_type, "Dog")

        new_cat = Cat.objects.create(name="Fluffy", age=3, color="White")
        self.assertEqual(new_cat.animal_type, "Cat")

    def test_from_db_method(self):
        """Test the from_db method for type conversion."""
        # Get a raw animal from the database
        animal = Animal.objects.filter(animal_type="Dog").first()

        # The from_db method should convert it to the correct type
        self.assertIsInstance(animal, Dog)
        self.assertEqual(animal.name, "Rex")

    def test_subtype_methods(self):
        """Test that subtype methods work correctly."""
        self.assertEqual(self.dog.bark(), "Rex says woof!")
        self.assertEqual(self.cat.meow(), "Whiskers says meow!")
        self.assertEqual(self.bird.fly(), "Tweety is flying!")

    def test_get_type_field_name(self):
        """Test getting the type field name."""
        self.assertEqual(Animal.get_type_field_name(), "animal_type")
        self.assertEqual(Vehicle.get_type_field_name(), "vehicle_kind")

        # Test default fallback
        class GenericModel(TypedModel):
            name = models.CharField(max_length=100)

            class Meta:
                abstract = True

        self.assertEqual(GenericModel.get_type_field_name(), "model_type")


class TypeFieldTestCase(TestCase):
    """Test case for TypeField functionality."""

    def test_type_field_defaults(self):
        """Test TypeField default configuration."""
        field = TypeField()
        self.assertFalse(field.editable)
        self.assertTrue(field.db_index)
        self.assertEqual(field.max_length, 100)

    def test_type_field_custom_configuration(self):
        """Test TypeField with custom configuration."""
        field = TypeField(max_length=50, editable=True, db_index=False)
        self.assertTrue(field.editable)
        self.assertFalse(field.db_index)
        self.assertEqual(field.max_length, 50)

    def test_type_field_value_conversion(self):
        """Test TypeField value conversion methods."""
        field = TypeField()

        # Test to_python
        self.assertEqual(field.to_python("Dog"), "Dog")
        self.assertEqual(field.to_python(Dog), "Dog")
        self.assertIsNone(field.to_python(None))

        # Test get_prep_value
        self.assertEqual(field.get_prep_value("Dog"), "Dog")
        self.assertEqual(field.get_prep_value(Dog), "Dog")
        self.assertIsNone(field.get_prep_value(None))

    def test_type_field_validation(self):
        """Test TypeField validation."""
        field = TypeField()

        # Create a mock model instance with typed_models
        class MockModel:
            class Meta:
                typed_models = {"Dog": Dog, "Cat": Cat}

        mock_instance = MockModel()

        # Valid types should pass
        field.validate("Dog", mock_instance)
        field.validate("Cat", mock_instance)

        # Invalid types should raise ValidationError
        with self.assertRaises(ValidationError):
            field.validate("InvalidType", mock_instance)
