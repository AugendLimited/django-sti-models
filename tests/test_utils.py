"""
Tests for utility functions.
"""

from django.test import TestCase
from django.db import models

from django_sti_models import TypedModel, TypeField
from django_sti_models.utils import (
    get_typed_queryset,
    create_typed_instance,
    get_type_hierarchy,
    validate_type_registration,
    get_type_field_value,
    is_typed_instance,
)
from django_sti_models.exceptions import STIException


class Animal(TypedModel):
    """Base animal model for testing utilities."""
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    type = TypeField()
    
    class Meta:
        abstract = True


class Dog(Animal):
    """Dog subtype for testing utilities."""
    breed = models.CharField(max_length=50)


class Cat(Animal):
    """Cat subtype for testing utilities."""
    color = models.CharField(max_length=30)


class Bird(Animal):
    """Bird subtype for testing utilities."""
    wingspan = models.FloatField()


class RegularModel(models.Model):
    """Regular Django model for testing."""
    name = models.CharField(max_length=100)


class UtilsTestCase(TestCase):
    """Test case for utility functions."""
    
    def setUp(self):
        """Set up test data."""
        self.dog = Dog.objects.create(
            name="Rex",
            age=3,
            breed="Golden Retriever"
        )
        self.cat = Cat.objects.create(
            name="Whiskers",
            age=2,
            color="Orange"
        )
        self.bird = Bird.objects.create(
            name="Tweety",
            age=1,
            wingspan=12.5
        )
    
    def test_get_typed_queryset_all_types(self):
        """Test getting queryset for all types."""
        queryset = get_typed_queryset(Animal)
        self.assertEqual(queryset.count(), 3)
        
        # Check that all types are included
        type_names = [animal.type for animal in queryset]
        self.assertIn("Dog", type_names)
        self.assertIn("Cat", type_names)
        self.assertIn("Bird", type_names)
    
    def test_get_typed_queryset_filtered(self):
        """Test getting queryset filtered by specific types."""
        # Filter by Dog and Cat only
        queryset = get_typed_queryset(Animal, ["Dog", "Cat"])
        self.assertEqual(queryset.count(), 2)
        
        type_names = [animal.type for animal in queryset]
        self.assertIn("Dog", type_names)
        self.assertIn("Cat", type_names)
        self.assertNotIn("Bird", type_names)
    
    def test_get_typed_queryset_single_type(self):
        """Test getting queryset for a single type."""
        queryset = get_typed_queryset(Animal, ["Dog"])
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().type, "Dog")
    
    def test_get_typed_queryset_empty_filter(self):
        """Test getting queryset with empty filter."""
        queryset = get_typed_queryset(Animal, [])
        self.assertEqual(queryset.count(), 0)
    
    def test_create_typed_instance(self):
        """Test creating typed instances."""
        # Create a new dog
        new_dog = create_typed_instance(
            Animal,
            "Dog",
            name="Buddy",
            age=5,
            breed="Labrador"
        )
        
        self.assertIsInstance(new_dog, Dog)
        self.assertEqual(new_dog.name, "Buddy")
        self.assertEqual(new_dog.age, 5)
        self.assertEqual(new_dog.breed, "Labrador")
        self.assertEqual(new_dog.type, "Dog")
        
        # Create a new cat
        new_cat = create_typed_instance(
            Animal,
            "Cat",
            name="Fluffy",
            age=3,
            color="White"
        )
        
        self.assertIsInstance(new_cat, Cat)
        self.assertEqual(new_cat.name, "Fluffy")
        self.assertEqual(new_cat.color, "White")
        self.assertEqual(new_cat.type, "Cat")
    
    def test_create_typed_instance_invalid_type(self):
        """Test creating typed instance with invalid type."""
        with self.assertRaises(STIException):
            create_typed_instance(
                Animal,
                "InvalidType",
                name="Invalid",
                age=1
            )
    
    def test_get_type_hierarchy(self):
        """Test getting type hierarchy."""
        hierarchy = get_type_hierarchy(Animal)
        
        # Check that all types are in the hierarchy
        self.assertIn("Dog", hierarchy)
        self.assertIn("Cat", hierarchy)
        self.assertIn("Bird", hierarchy)
        
        # Check that each type has the correct parent
        self.assertEqual(hierarchy["Dog"], [])
        self.assertEqual(hierarchy["Cat"], [])
        self.assertEqual(hierarchy["Bird"], [])
    
    def test_validate_type_registration_valid(self):
        """Test validation of valid type registration."""
        errors = validate_type_registration(Animal)
        self.assertEqual(len(errors), 0)
    
    def test_validate_type_registration_no_types(self):
        """Test validation when no types are registered."""
        # Create a base model without any subtypes
        class EmptyAnimal(TypedModel):
            name = models.CharField(max_length=100)
            type = TypeField()
            
            class Meta:
                abstract = True
        
        errors = validate_type_registration(EmptyAnimal)
        self.assertIn("No types registered for this model", errors)
    
    def test_get_type_field_value(self):
        """Test getting type field value from instances."""
        # Test with standard type field
        self.assertEqual(get_type_field_value(self.dog), "Dog")
        self.assertEqual(get_type_field_value(self.cat), "Cat")
        self.assertEqual(get_type_field_value(self.bird), "Bird")
        
        # Test with None value
        empty_animal = Animal()
        self.assertIsNone(get_type_field_value(empty_animal))
    
    def test_get_type_field_value_custom_field_name(self):
        """Test getting type field value with custom field name."""
        # Create a model with custom type field name
        class Vehicle(TypedModel):
            name = models.CharField(max_length=100)
            vehicle_type = TypeField()
            
            class Meta:
                abstract = True
        
        class Car(Vehicle):
            doors = models.IntegerField()
        
        car = Car.objects.create(name="Tesla", doors=4)
        self.assertEqual(get_type_field_value(car), "Car")
    
    def test_is_typed_instance(self):
        """Test checking if an instance is a typed model."""
        # Test with typed instances
        self.assertTrue(is_typed_instance(self.dog))
        self.assertTrue(is_typed_instance(self.cat))
        self.assertTrue(is_typed_instance(self.bird))
        
        # Test with regular Django model
        regular_model = RegularModel(name="Regular")
        self.assertFalse(is_typed_instance(regular_model))
        
        # Test with base typed model
        base_animal = Animal(name="Base", age=1)
        self.assertTrue(is_typed_instance(base_animal))
    
    def test_is_typed_instance_no_type_field(self):
        """Test checking typed instance without type field."""
        # Create a model that inherits from TypedModel but has no type field
        class NoTypeField(TypedModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                abstract = True
        
        class SubType(NoTypeField):
            pass
        
        instance = SubType(name="Test")
        # This should still be considered a typed instance
        self.assertTrue(is_typed_instance(instance)) 