#!/usr/bin/env python
"""
Comprehensive test script for the improved django-sti-models framework.

This script demonstrates and validates the STI functionality.
Run this in a Django shell or as a management command.
"""

import os
import sys
import django
from django.conf import settings
from django.db import connection

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django_sti_models',
            'examples',
        ],
        USE_TZ=True,
    )

django.setup()

from django.core.management import execute_from_command_line
from examples.business_models import Business, BusinessExtension, PremiumBusiness


def create_tables():
    """Create database tables for testing."""
    print("Creating database tables...")
    
    with connection.schema_editor() as schema_editor:
        # Create Business table (the STI base)
        schema_editor.create_model(Business)
        
        # BusinessExtension and PremiumBusiness should NOT create separate tables
        # They should share the Business table
    
    print("✓ Tables created successfully")


def test_sti_table_sharing():
    """Test that STI models share the same database table."""
    print("\n=== Testing STI Table Sharing ===")
    
    # Get table names
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    premium_table = PremiumBusiness._meta.db_table
    
    print(f"Business table: {business_table}")
    print(f"BusinessExtension table: {extension_table}")
    print(f"PremiumBusiness table: {premium_table}")
    
    # All should be the same
    if business_table == extension_table == premium_table:
        print("✓ All models share the same table (STI working correctly)")
    else:
        print("✗ Models have different tables (STI not working)")
        return False
    
    # Check that only one table exists in the database
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%business%';")
        tables = cursor.fetchall()
        
    print(f"Database tables: {[table[0] for table in tables]}")
    
    if len(tables) == 1:
        print("✓ Only one business table exists in database")
        return True
    else:
        print(f"✗ Expected 1 table, found {len(tables)}")
        return False


def test_type_registration():
    """Test that types are properly registered."""
    print("\n=== Testing Type Registration ===")
    
    all_types = Business.get_all_types()
    expected_types = {'Business', 'BusinessExtension', 'PremiumBusiness'}
    
    print(f"Registered types: {set(all_types.keys())}")
    print(f"Expected types: {expected_types}")
    
    if set(all_types.keys()) == expected_types:
        print("✓ All types registered correctly")
        return True
    else:
        print("✗ Type registration incomplete")
        return False


def test_instance_creation():
    """Test creating instances of different types."""
    print("\n=== Testing Instance Creation ===")
    
    # Create instances
    business = Business.objects.create(name="Regular Corp", description="A regular business")
    extension = BusinessExtension.objects.create(
        name="Extended Corp", 
        description="An extended business",
        cif_number="B12345678"
    )
    premium = PremiumBusiness.objects.create(
        name="Premium Corp",
        description="A premium business", 
        premium_level="gold"
    )
    
    print(f"Created business: {business} (Type: {business.model_type})")
    print(f"Created extension: {extension} (Type: {extension.model_type})")
    print(f"Created premium: {premium} (Type: {premium.model_type})")
    
    # Verify type fields are set correctly
    if (business.model_type == "Business" and 
        extension.model_type == "BusinessExtension" and
        premium.model_type == "PremiumBusiness"):
        print("✓ Type fields set correctly")
        return business, extension, premium
    else:
        print("✗ Type fields not set correctly")
        return None


def test_type_aware_querying(business, extension, premium):
    """Test type-aware querying."""
    print("\n=== Testing Type-Aware Querying ===")
    
    # Query all businesses
    all_businesses = Business.objects.all()
    print(f"All businesses: {all_businesses.count()} (should be 3)")
    
    # Query specific types
    regular_businesses = Business.objects.filter(model_type="Business")
    extension_businesses = BusinessExtension.objects.all()
    premium_businesses = PremiumBusiness.objects.all()
    
    print(f"Regular businesses: {regular_businesses.count()} (should be 1)")
    print(f"Extension businesses: {extension_businesses.count()} (should be 1)")
    print(f"Premium businesses: {premium_businesses.count()} (should be 1)")
    
    # Verify correct instances are returned
    success = (
        all_businesses.count() == 3 and
        regular_businesses.count() == 1 and
        extension_businesses.count() == 1 and
        premium_businesses.count() == 1
    )
    
    if success:
        print("✓ Type-aware querying working correctly")
    else:
        print("✗ Type-aware querying not working")
    
    return success


def test_polymorphic_behavior(business, extension, premium):
    """Test polymorphic behavior."""
    print("\n=== Testing Polymorphic Behavior ===")
    
    # Get all businesses and check their real instances
    all_businesses = Business.objects.all()
    
    success = True
    for biz in all_businesses:
        real_instance = biz.get_real_instance()
        expected_class = biz.model_type
        actual_class = real_instance.__class__.__name__
        
        print(f"{biz.name}: {biz.__class__.__name__} -> {actual_class} (expected: {expected_class})")
        
        if actual_class != expected_class:
            success = False
    
    if success:
        print("✓ Polymorphic behavior working correctly")
    else:
        print("✗ Polymorphic behavior not working")
    
    return success


def test_field_access():
    """Test that subclass-specific fields are accessible."""
    print("\n=== Testing Field Access ===")
    
    # Get instances
    extension = BusinessExtension.objects.first()
    premium = PremiumBusiness.objects.first()
    
    success = True
    
    # Test extension fields
    try:
        cif = extension.cif_number
        print(f"Extension CIF: {cif}")
    except AttributeError:
        print("✗ Cannot access BusinessExtension.cif_number")
        success = False
    
    # Test premium fields
    try:
        level = premium.premium_level
        print(f"Premium level: {level}")
    except AttributeError:
        print("✗ Cannot access PremiumBusiness.premium_level")
        success = False
    
    if success:
        print("✓ Subclass fields accessible")
    
    return success


def test_sti_validation():
    """Test STI setup validation."""
    print("\n=== Testing STI Validation ===")
    
    models_to_test = [Business, BusinessExtension, PremiumBusiness]
    all_valid = True
    
    for model in models_to_test:
        errors = model.validate_sti_setup()
        if errors:
            print(f"✗ {model.__name__}: {errors}")
            all_valid = False
        else:
            print(f"✓ {model.__name__}: Valid STI setup")
    
    return all_valid


def test_manager_methods():
    """Test custom manager methods."""
    print("\n=== Testing Manager Methods ===")
    
    # Test get_for_type
    extension_via_manager = Business.objects.get_for_type("BusinessExtension")
    print(f"Extensions via get_for_type: {extension_via_manager.count()}")
    
    # Test exclude_types
    non_premium = Business.objects.exclude_types("PremiumBusiness")
    print(f"Non-premium businesses: {non_premium.count()}")
    
    success = (extension_via_manager.count() == 1 and non_premium.count() == 2)
    
    if success:
        print("✓ Manager methods working correctly")
    else:
        print("✗ Manager methods not working")
    
    return success


def run_all_tests():
    """Run all STI tests."""
    print("🚀 Starting Django STI Models Framework Tests\n")
    
    # Create tables
    create_tables()
    
    # Run tests
    tests = [
        test_sti_table_sharing,
        test_type_registration,
        test_instance_creation,
    ]
    
    results = []
    business = extension = premium = None
    
    for test in tests:
        try:
            result = test()
            if test == test_instance_creation:
                business, extension, premium = result if result else (None, None, None)
                result = result is not None
            results.append(result)
        except Exception as e:
            print(f"✗ {test.__name__} failed with error: {e}")
            results.append(False)
    
    # Tests that need instances
    if business and extension and premium:
        dependent_tests = [
            lambda: test_type_aware_querying(business, extension, premium),
            lambda: test_polymorphic_behavior(business, extension, premium),
            test_field_access,
            test_sti_validation,
            test_manager_methods,
        ]
        
        for test in dependent_tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"✗ {test.__name__} failed with error: {e}")
                results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! STI framework is working correctly.")
    else:
        print("❌ Some tests failed. STI framework needs attention.")
    
    return passed == total


if __name__ == "__main__":
    run_all_tests()