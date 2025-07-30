"""
Improved Business models demonstrating proper STI usage.

This example shows how to correctly implement Single Table Inheritance
with the enhanced django-sti-models framework.
"""

from django.db import models
from django_sti_models import TypedModel, TypeField


# Mock external dependencies for the example
class AuditableModel(models.Model):
    """Mock auditable model for demonstration."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class CloneMixin:
    """Mock clone mixin for demonstration."""
    def clone(self):
        return self


class HookModelMixin:
    """Mock hook mixin for demonstration."""
    pass


class AugendModel(AuditableModel, CloneMixin, HookModelMixin):
    """
    Abstract base model with common functionality.
    
    Important: This does NOT inherit from TypedModel yet, 
    and has no TypeField. That comes in the concrete base.
    """
    
    class Meta:
        abstract = True


class Business(TypedModel, AugendModel):
    """
    Concrete STI base model.
    
    This is the model that:
    1. Creates the actual database table
    2. Contains the TypeField for STI
    3. All subclasses will share this table
    
    Note: Do NOT make this abstract!
    """
    # STI type field - this differentiates between Business types
    model_type = TypeField()
    
    # Business fields
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Business"
        verbose_name_plural = "Businesses"
        # Important: Do NOT set abstract = True here!

    def __str__(self):
        return self.name

    def get_business_info(self):
        """Base method that can be overridden by subclasses."""
        return f"Business: {self.name}"


class BusinessExtension(Business):
    """
    STI subclass of Business.
    
    This model:
    1. Shares the Business table (no separate table created)
    2. Uses model_type field to differentiate from Business
    3. Can have additional fields (stored in same table)
    4. Inherits all Business functionality
    """
    # Additional fields specific to BusinessExtension
    cif_number = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Business Extension"
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return f"{self.name} (Extended)"

    def get_business_info(self):
        """Override base method with extension-specific info."""
        base_info = super().get_business_info()
        return f"{base_info} - CIF: {self.cif_number}"


class PremiumBusiness(Business):
    """
    Another STI subclass of Business.
    
    Demonstrates multiple subclasses sharing the same table.
    """
    # Premium-specific fields
    premium_level = models.CharField(
        max_length=20,
        choices=[
            ('gold', 'Gold'),
            ('platinum', 'Platinum'),
            ('diamond', 'Diamond'),
        ],
        default='gold'
    )
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Premium Business"
        verbose_name_plural = "Premium Businesses"

    def __str__(self):
        return f"{self.name} ({self.get_premium_level_display()})"

    def get_business_info(self):
        """Override base method with premium-specific info."""
        base_info = super().get_business_info()
        return f"{base_info} - Premium Level: {self.get_premium_level_display()}"


# Usage demonstration functions
def demonstrate_sti_usage():
    """
    Demonstrate how the improved STI models work.
    """
    print("=== STI Business Models Demo ===\n")
    
    # Create different types of businesses
    regular_business = Business.objects.create(
        name="Acme Corp",
        description="A regular business"
    )
    
    extended_business = BusinessExtension.objects.create(
        name="Tech Solutions Inc",
        description="An extended business",
        cif_number="B12345678",
        tax_id="TAX123456"
    )
    
    premium_business = PremiumBusiness.objects.create(
        name="Elite Enterprises",
        description="A premium business",
        premium_level="platinum",
        annual_revenue=1000000.00
    )
    
    print("Created businesses:")
    print(f"  - {regular_business} (Type: {regular_business.model_type})")
    print(f"  - {extended_business} (Type: {extended_business.model_type})")
    print(f"  - {premium_business} (Type: {premium_business.model_type})")
    print()
    
    # Demonstrate querying
    print("All businesses (from base model):")
    all_businesses = Business.objects.all()
    for business in all_businesses:
        print(f"  - {business.get_business_info()}")
    print()
    
    # Demonstrate type-specific querying
    print("Extended businesses only:")
    extended_businesses = BusinessExtension.objects.all()
    for business in extended_businesses:
        print(f"  - {business.get_business_info()}")
    print()
    
    print("Premium businesses only:")
    premium_businesses = PremiumBusiness.objects.all()
    for business in premium_businesses:
        print(f"  - {business.get_business_info()}")
    print()
    
    # Demonstrate type registration
    print("Registered business types:")
    all_types = Business.get_all_types()
    for type_name, type_class in all_types.items():
        print(f"  - {type_name}: {type_class}")
    print()
    
    # Demonstrate polymorphic behavior
    print("Polymorphic behavior:")
    for business in Business.objects.all():
        real_instance = business.get_real_instance()
        print(f"  - {business.name}: {business.__class__.__name__} -> {real_instance.__class__.__name__}")
    print()
    
    # Demonstrate validation
    print("STI setup validation:")
    for model_class in [Business, BusinessExtension, PremiumBusiness]:
        errors = model_class.validate_sti_setup()
        if errors:
            print(f"  - {model_class.__name__}: {errors}")
        else:
            print(f"  - {model_class.__name__}: ✓ Valid STI setup")


if __name__ == "__main__":
    # This would be run in a Django shell or management command
    demonstrate_sti_usage() 