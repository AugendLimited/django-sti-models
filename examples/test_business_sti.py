"""
Test script to demonstrate STI working with Business models.
"""

from .business_models import Business, BusinessExtension


def test_business_sti():
    """Test that STI works correctly with Business models."""
    
    # Create a regular business
    business = Business.objects.create(name="Acme Corp")
    print(f"Created business: {business}")
    print(f"Business type: {business.model_type}")
    print(f"Business class: {business.__class__.__name__}")
    print()
    
    # Create a business extension
    business_ext = BusinessExtension.objects.create(
        name="Tech Solutions Inc", 
        cif_number="B12345678"
    )
    print(f"Created business extension: {business_ext}")
    print(f"Business extension type: {business_ext.model_type}")
    print(f"Business extension class: {business_ext.__class__.__name__}")
    print(f"CIF number: {business_ext.cif_number}")
    print()
    
    # Query all businesses (both types)
    all_businesses = Business.objects.all()
    print(f"All businesses ({all_businesses.count()} total):")
    for biz in all_businesses:
        print(f"  - {biz.name} (type: {biz.model_type}, class: {biz.__class__.__name__})")
    print()
    
    # Query only Business instances
    regular_businesses = Business.objects.filter(model_type="Business")
    print(f"Regular businesses ({regular_businesses.count()}):")
    for biz in regular_businesses:
        print(f"  - {biz.name}")
    print()
    
    # Query only BusinessExtension instances
    extension_businesses = BusinessExtension.objects.all()
    print(f"Business extensions ({extension_businesses.count()}):")
    for biz in extension_businesses:
        print(f"  - {biz.name} (CIF: {biz.cif_number})")
    print()
    
    # Test type registration
    print("Registered types:")
    registered_types = Business.get_all_types()
    for type_name, type_class in registered_types.items():
        print(f"  - {type_name}: {type_class}")
    print()
    
    # Test getting real instances
    print("Getting real instances:")
    for biz in Business.objects.all():
        real_biz = biz.get_real_instance()
        print(f"  - {biz.name} is actually a {real_biz.__class__.__name__}")


if __name__ == "__main__":
    # This would be run in a Django shell
    test_business_sti() 