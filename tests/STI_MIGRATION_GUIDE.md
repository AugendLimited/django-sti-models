# Django STI Models - Migration Guide

## Framework Improvements Summary

The django-sti-models framework has been completely rewritten to provide robust Single Table Inheritance (STI) support. Here are the key improvements:

### ✅ What's Fixed

1. **True STI Implementation**: All subclasses now properly share a single database table
2. **Migration Safety**: No more separate tables created for subclasses
3. **Thread-Safe Type Registration**: Improved type registration system
4. **Enhanced Manager**: Better type-aware querying and performance
5. **Robust Validation**: Comprehensive STI setup validation
6. **Polymorphic Behavior**: Proper type conversion and instance handling

### 🔧 Breaking Changes

1. **Model Structure**: Base STI models must NOT be abstract
2. **Type Registration**: Improved automatic type registration
3. **Manager Methods**: Enhanced manager with new methods
4. **Validation**: Stricter type field validation

## Migration Steps

### 1. Update Your Model Structure

**❌ Old (Incorrect) Pattern:**
```python
class Business(TypedModel, AugendModel):
    name = models.CharField(max_length=255)
    model_type = TypeField()
    
    class Meta:
        abstract = True  # ❌ This is wrong!
        verbose_name_plural = "Businesses"

class BusinessExtension(Business):
    cif_number = models.CharField(max_length=255, blank=True)
```

**✅ New (Correct) Pattern:**
```python
class Business(TypedModel, AugendModel):
    """Concrete STI base model - creates the actual table."""
    name = models.CharField(max_length=255)
    model_type = TypeField()
    
    class Meta:
        verbose_name_plural = "Businesses"
        # ✅ Do NOT set abstract = True!

class BusinessExtension(Business):
    """STI subclass - shares Business table."""
    cif_number = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name_plural = "Business Extensions"
```

### 2. Fix Existing Migrations

If you have existing migrations that created separate tables:

```bash
# Remove incorrect migrations
rm your_app/migrations/0001_initial.py

# Create new migrations with correct STI structure
python manage.py makemigrations

# This should create only ONE table for the base model
python manage.py migrate
```

### 3. Update Your Code Usage

**Enhanced Manager Methods:**
```python
# New methods available
Business.objects.get_for_type("BusinessExtension")
Business.objects.exclude_types("PremiumBusiness")

# Type-aware querying (works automatically)
BusinessExtension.objects.all()  # Only returns BusinessExtension instances
```

**New Validation Methods:**
```python
# Validate STI setup
errors = Business.validate_sti_setup()
if errors:
    print(f"STI setup issues: {errors}")

# Check if model is part of STI hierarchy
if Business.is_sti_model():
    print("This is an STI model")
```

**Enhanced Instance Methods:**
```python
# Get the correct typed instance
real_instance = business.get_real_instance()

# Get human-readable type name
display_name = business.get_type_display_name()

# Create typed instances
premium = Business.create_typed_instance("PremiumBusiness", name="Elite Corp")
```

### 4. Verification Steps

Run this test to verify STI is working:

```python
def verify_sti_working():
    # 1. Check table sharing
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    
    assert business_table == extension_table, "Tables should be the same!"
    
    # 2. Check type registration
    all_types = Business.get_all_types()
    assert "Business" in all_types
    assert "BusinessExtension" in all_types
    
    # 3. Check instance creation
    business = Business.objects.create(name="Test Corp")
    extension = BusinessExtension.objects.create(name="Test Ext", cif_number="B123")
    
    assert business.model_type == "Business"
    assert extension.model_type == "BusinessExtension"
    
    # 4. Check querying
    all_businesses = Business.objects.all()
    only_extensions = BusinessExtension.objects.all()
    
    assert all_businesses.count() == 2
    assert only_extensions.count() == 1
    
    print("✅ STI is working correctly!")
```

### 5. Common Issues and Solutions

**Issue: AttributeError: 'Options' object has no attribute 'get_db_table'**
```python
# This was a bug in the framework that has been fixed
# Solution: Update to the latest version of django-sti-models
# The fix simplifies table inheritance without overriding Django internals
```

**Issue: Separate tables still being created**
```python
# Solution: Ensure base model is NOT abstract
class Business(TypedModel):
    class Meta:
        # abstract = True  # ❌ Remove this line
        pass
```

**Issue: Type field not set automatically**
```python
# Solution: Type field is now set automatically in __init__ and save()
# No manual intervention needed
```

**Issue: Polymorphic queries not working**
```python
# Solution: Use get_real_instance() for correct type conversion
for business in Business.objects.all():
    real_instance = business.get_real_instance()
    # real_instance will be the correct subclass type
```

**Issue: Migration creates separate tables**
```python
# Solution: Check STI setup before running migrations
errors = YourModel.validate_sti_setup()
if errors:
    print(f"Fix these issues first: {errors}")

# Also check table configuration
table_info = YourModel.get_sti_table_info()
print(f"Table configuration: {table_info}")
```

## New Features

### 1. STI Base Model Detection
```python
# Get the base STI model for any subclass
base_model = BusinessExtension.get_sti_base_model()
assert base_model == Business
```

### 2. Type Statistics
```python
from django_sti_models.utils import get_type_statistics

stats = get_type_statistics(Business)
# Returns: {"Business": 5, "BusinessExtension": 3, "PremiumBusiness": 2}
```

### 3. Enhanced Admin Integration
```python
from django.contrib import admin
from django_sti_models.admin import TypedModelAdmin

@admin.register(Business)
class BusinessAdmin(TypedModelAdmin):
    list_display = ['name', 'model_type', 'created_at']
    list_filter = ['model_type']
```

### 4. Validation Utilities
```python
from django_sti_models.utils import validate_type_consistency

errors = validate_type_consistency(Business)
if errors:
    print(f"Data consistency issues: {errors}")
```

## Performance Improvements

1. **Indexed Type Field**: Automatic database indexing for better query performance
2. **Optimized Queries**: Type-aware filtering reduces unnecessary data retrieval
3. **Cached Type Registration**: Thread-safe caching of type information
4. **Efficient Polymorphic Conversion**: Optimized instance type conversion

## Testing Your Migration

Use the provided test script to validate your STI implementation:

```bash
python test_improved_sti.py
```

This will run comprehensive tests to ensure:
- ✅ Single table sharing
- ✅ Type registration
- ✅ Polymorphic behavior
- ✅ Type-aware querying
- ✅ Field access
- ✅ Manager methods

## Need Help?

If you encounter issues during migration:

1. Check the examples in `examples/business_models.py`
2. Run the validation script: `python test_improved_sti.py`
3. Use the built-in validation: `YourModel.validate_sti_setup()`
4. Review the migration guide above

The improved framework is designed to be backward-compatible where possible, but the model structure changes are necessary for proper STI functionality.