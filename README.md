# Django STI Models

An improved implementation of Single Table Inheritance (STI) for Django with better monkey patching, type safety, and performance.

## Features

- **Improved Monkey Patching**: Cleaner metaclass implementation that's more maintainable and less prone to conflicts
- **Type Safety**: Full type hints and validation throughout the codebase
- **Better Performance**: Optimized type registration and lookup mechanisms with caching
- **Enhanced Error Handling**: Comprehensive exception handling with meaningful error messages
- **Cleaner API**: More intuitive interface for working with typed models
- **Validation**: Built-in validation for type registration and field configuration
- **Django Admin Integration**: Seamless admin interface with type-aware filtering and forms
- **Management Commands**: Built-in commands for validation and maintenance
- **Advanced Utilities**: Comprehensive utility functions for common operations
- **Type Statistics**: Built-in support for analyzing type distribution

## Installation

```bash
# Using Poetry (recommended)
poetry add django-sti-models

# Using pip
pip install django-sti-models
```

## Quick Start

### 1. Define Your Base Model

```python
from django_sti_models import TypedModel, TypeField

class Animal(TypedModel):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    animal_type = TypeField()  # Use descriptive field names!
    
    class Meta:
        abstract = True
```

### 2. Create Your Subtypes

```python
class Dog(Animal):
    breed = models.CharField(max_length=50)
    
    def bark(self):
        return f"{self.name} says woof!"

class Cat(Animal):
    color = models.CharField(max_length=30)
    
    def meow(self):
        return f"{self.name} says meow!"

class Bird(Animal):
    wingspan = models.FloatField()
    
    def fly(self):
        return f"{self.name} is flying!"
```

### 3. Use Your Typed Models

```python
# Create instances
dog = Dog.objects.create(name="Rex", age=3, breed="Golden Retriever")
cat = Cat.objects.create(name="Whiskers", age=2, color="Orange")
bird = Bird.objects.create(name="Tweety", age=1, wingspan=12.5)

# Query by type
dogs = Dog.objects.all()  # Only returns Dog instances
cats = Cat.objects.all()  # Only returns Cat instances

# Query all animals
all_animals = Animal.objects.all()  # Returns all types

# Get the real instance type
animal = Animal.objects.first()
real_animal = animal.get_real_instance()  # Returns the correct subtype

# Check available types
available_types = Animal.get_all_types()
# Returns: {'Dog': <class 'Dog'>, 'Cat': <class 'Cat'>, 'Bird': <class 'Bird'>}
```

## Advanced Usage

### Custom Type Field Names

You can use a custom field name for the type field:

```python
class Vehicle(TypedModel):
    name = models.CharField(max_length=100)
    vehicle_kind = TypeField()  # Custom field name
    
    class Meta:
        abstract = True

class Car(Vehicle):
    doors = models.IntegerField()

class Motorcycle(Vehicle):
    engine_size = models.FloatField()
```

### Django Admin Integration

The package provides seamless Django admin integration:

```python
from django_sti_models import TypedModelAdmin, register_typed_models

# Option 1: Automatic registration
register_typed_models(Vehicle)

# Option 2: Custom admin class
class VehicleAdmin(TypedModelAdmin):
    list_display = ['name', 'vehicle_kind', 'created_at']
    list_filter = ['vehicle_kind']
    search_fields = ['name']

# Register with admin
admin.site.register(Vehicle, VehicleAdmin)
```

### Management Commands

Use built-in management commands for validation and maintenance:

```bash
# Validate all STI models
python manage.py validate_sti_models

# Validate specific app
python manage.py validate_sti_models --app myapp

# Show type statistics
python manage.py validate_sti_models --stats

# Validate specific model
python manage.py validate_sti_models --model Vehicle
```

### Advanced Utility Functions

```python
from django_sti_models.utils import (
    get_typed_queryset,
    create_typed_instance,
    get_type_hierarchy,
    get_type_statistics,
    filter_by_type,
    validate_type_consistency,
    migrate_type_field
)

# Get queryset filtered by specific types
land_vehicles = get_typed_queryset(Vehicle, ['Car', 'Motorcycle'])

# Create instance by type name
car = create_typed_instance(Vehicle, 'Car', name='Tesla', doors=4)

# Get type hierarchy
hierarchy = get_type_hierarchy(Vehicle)

# Get type statistics
stats = get_type_statistics(Vehicle)
# Returns: {'Car': 10, 'Motorcycle': 5}

# Filter existing queryset by type
cars_only = filter_by_type(Vehicle.objects.all(), 'Car')

# Validate type consistency
errors = validate_type_consistency(Vehicle)

# Migrate type field data
updated_count = migrate_type_field(Vehicle, 'old_type', 'new_type')
```

### Type Validation

The package includes comprehensive validation:

```python
from django_sti_models.utils import validate_type_registration

# Validate your type registration
errors = validate_type_registration(Vehicle)
if errors:
    print("Validation errors:", errors)
```

## Field Naming Best Practices

**✅ Good field names:**
- `animal_type` (for Animal models)
- `content_type` (for Content models)
- `vehicle_kind` (for Vehicle models)
- `user_role` (for User models)
- `product_category` (for Product models)

**❌ Avoid these:**
- `type` (Python reserved word)
- `kind` (too generic)
- `category` (too generic)

**Benefits of descriptive names:**
- Clearer code intent
- Better IDE support
- Avoids Python reserved word conflicts
- More maintainable code

## Improvements Over Original

### 1. Better Monkey Patching

The original django-typed-models used aggressive monkey patching that could conflict with other Django apps. This implementation:

- Uses a cleaner metaclass approach
- Minimizes interference with Django's internals
- Provides better error handling for conflicts
- Is more maintainable and debuggable

### 2. Enhanced Type Safety

- Full type hints throughout the codebase
- Better validation of type registration
- Improved error messages for debugging
- Type-safe manager implementations
- Generic type support

### 3. Performance Optimizations

- More efficient type registration
- Optimized queryset filtering
- Reduced memory usage
- Better caching of type information
- LRU caching for frequently accessed data

### 4. Cleaner API

- More intuitive method names
- Better separation of concerns
- Comprehensive utility functions
- Improved documentation
- Enhanced manager methods (get_or_create, update_or_create)

### 5. Django Admin Integration

- Seamless admin interface
- Type-aware filtering and forms
- Automatic type field handling
- Validation tools
- Statistics display

### 6. Management Commands

- Built-in validation commands
- Type consistency checking
- Statistics reporting
- Maintenance utilities

## Configuration

### Django Settings

Add to your `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'django_sti_models',
]
```

### Type Field Configuration

The `TypeField` supports various configuration options:

```python
class MyModel(TypedModel):
    # Basic usage
    model_type = TypeField()
    
    # With custom configuration
    model_type = TypeField(
        max_length=50,
        db_index=True,
        editable=False
    )
```

### Admin Configuration

```python
# In your admin.py
from django_sti_models import TypedModelAdmin, register_typed_models

# For automatic registration
register_typed_models(YourBaseModel)

# For custom admin
class YourModelAdmin(TypedModelAdmin):
    list_display = ['name', 'model_type', 'created_at']
    list_filter = ['model_type']
    readonly_fields = ['model_type']
```

## Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=django_sti_models

# Run type checking
poetry run mypy django_sti_models/

# Run validation
python manage.py validate_sti_models
```

## Best Practices

### 1. Use Descriptive Type Field Names
```python
# Good
class Content(TypedModel):
    content_type = TypeField()

# Also good
class Vehicle(TypedModel):
    vehicle_kind = TypeField()
```

### 2. Implement Polymorphic Methods
```python
class Animal(TypedModel):
    def make_sound(self):
        raise NotImplementedError

class Dog(Animal):
    def make_sound(self):
        return "Woof!"

class Cat(Animal):
    def make_sound(self):
        return "Meow!"
```

### 3. Validate Type Consistency
```python
# Regular validation
from django_sti_models.utils import validate_type_consistency
errors = validate_type_consistency(Animal)

# Using management command
python manage.py validate_sti_models --app animals
```

### 4. Use Type-Aware Queries
```python
# Query specific types directly
dogs = Dog.objects.all()

# Use utility functions for complex filtering
land_animals = filter_by_type(Animal.objects.all(), ['Dog', 'Cat'])
```

### 5. Leverage Admin Integration
```python
# Automatic registration
register_typed_models(Animal)

# Custom admin with type-aware features
class AnimalAdmin(TypedModelAdmin):
    list_display = ['name', 'animal_type', 'age']
    list_filter = ['animal_type']
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

This project is inspired by and improves upon the original [django-typed-models](https://github.com/craigds/django-typed-models) by Craig de Stigter. 