"""
Tests for Django Admin integration.
"""

from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.db import models
from django.test import RequestFactory, TestCase

from django_sti_models import (
    TypedModel,
    TypedModelAdmin,
    TypeField,
    register_typed_models,
)


class Animal(TypedModel):
    """Base animal model for testing admin."""

    name = models.CharField(max_length=100)
    age = models.IntegerField()
    type = TypeField()

    class Meta:
        abstract = True


class Dog(Animal):
    """Dog subtype for testing admin."""

    breed = models.CharField(max_length=50)

    def bark(self):
        return f"{self.name} says woof!"


class Cat(Animal):
    """Cat subtype for testing admin."""

    color = models.CharField(max_length=30)

    def meow(self):
        return f"{self.name} says meow!"


class TypedModelAdminTestCase(TestCase):
    """Test case for TypedModelAdmin functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.admin_site = AdminSite()

        # Create test instances
        self.dog = Dog.objects.create(name="Rex", age=3, breed="Golden Retriever")
        self.cat = Cat.objects.create(name="Whiskers", age=2, color="Orange")

    def test_typed_model_admin_list_filter(self):
        """Test that type filter is automatically added."""
        admin_class = TypedModelAdmin(Animal, self.admin_site)
        filters = admin_class.get_list_filter(self.factory.get("/"))

        self.assertIn("type", filters)

    def test_typed_model_admin_queryset(self):
        """Test that admin queryset is properly filtered."""
        # Test base model admin
        base_admin = TypedModelAdmin(Animal, self.admin_site)
        base_queryset = base_admin.get_queryset(self.factory.get("/"))

        # Should return all animals
        self.assertEqual(base_queryset.count(), 2)

        # Test specific type admin
        dog_admin = TypedModelAdmin(Dog, self.admin_site)
        dog_queryset = dog_admin.get_queryset(self.factory.get("/"))

        # Should only return dogs
        self.assertEqual(dog_queryset.count(), 1)
        self.assertEqual(dog_queryset.first(), self.dog)

    def test_typed_model_admin_readonly_fields(self):
        """Test that type field is automatically readonly."""
        admin_class = TypedModelAdmin(Animal, self.admin_site)
        readonly_fields = admin_class.get_readonly_fields(self.factory.get("/"))

        self.assertIn("type", readonly_fields)

    def test_typed_model_admin_save_model(self):
        """Test that type field is set when saving."""
        admin_class = TypedModelAdmin(Dog, self.admin_site)

        # Create a new dog instance
        new_dog = Dog(name="Buddy", age=5, breed="Labrador")

        # Save through admin
        admin_class.save_model(
            request=self.factory.get("/"), obj=new_dog, form=None, change=False
        )

        # Type field should be set
        self.assertEqual(new_dog.type, "Dog")

    def test_register_typed_models(self):
        """Test automatic registration of typed models."""
        # Register all animal types
        register_typed_models(Animal, self.admin_site)

        # Check that both types are registered
        self.assertIn(Dog, self.admin_site._registry)
        self.assertIn(Cat, self.admin_site._registry)

        # Check that admin classes are properly configured
        dog_admin = self.admin_site._registry[Dog]
        cat_admin = self.admin_site._registry[Cat]

        self.assertIsInstance(dog_admin, TypedModelAdmin)
        self.assertIsInstance(cat_admin, TypedModelAdmin)


class TypedModelFormTestCase(TestCase):
    """Test case for TypedModelForm functionality."""

    def test_typed_model_form_choices(self):
        """Test that form includes type choices."""
        from django_sti_models.admin import TypedModelForm

        class TestForm(TypedModelForm):
            class Meta:
                model = Animal
                fields = "__all__"

        form = TestForm()

        # Type field should have choices
        type_field = form.fields.get("type")
        if type_field:
            self.assertTrue(len(type_field.choices) > 0)

    def test_typed_model_form_validation(self):
        """Test form validation with type field."""
        from django_sti_models.admin import TypedModelForm

        class TestForm(TypedModelForm):
            class Meta:
                model = Animal
                fields = "__all__"

        # Valid data
        valid_data = {"name": "Test Animal", "age": 5, "type": "Dog"}
        form = TestForm(data=valid_data)
        self.assertTrue(form.is_valid())

        # Invalid type
        invalid_data = {"name": "Test Animal", "age": 5, "type": "InvalidType"}
        form = TestForm(data=invalid_data)
        self.assertFalse(form.is_valid())


class TypeFilterTestCase(TestCase):
    """Test case for TypeFilter functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

        # Create test instances
        self.dog = Dog.objects.create(name="Rex", age=3, breed="Golden Retriever")
        self.cat = Cat.objects.create(name="Whiskers", age=2, color="Orange")

    def test_type_filter_lookups(self):
        """Test that filter provides correct lookups."""
        from django_sti_models.admin import TypeFilter

        filter_instance = TypeFilter()

        # Mock admin
        class MockAdmin:
            model = Animal

        lookups = filter_instance.lookups(self.factory.get("/"), MockAdmin())

        # Should include both types
        type_names = [lookup[0] for lookup in lookups]
        self.assertIn("Dog", type_names)
        self.assertIn("Cat", type_names)

    def test_type_filter_queryset(self):
        """Test that filter properly filters queryset."""
        from django_sti_models.admin import TypeFilter

        filter_instance = TypeFilter()

        # Mock admin
        class MockAdmin:
            model = Animal

        # Test filtering by Dog
        request = self.factory.get("/?type=Dog")
        queryset = filter_instance.queryset(request, Animal.objects.all())

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.dog)

        # Test filtering by Cat
        request = self.factory.get("/?type=Cat")
        queryset = filter_instance.queryset(request, Animal.objects.all())

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.cat)
