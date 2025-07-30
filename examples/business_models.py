"""
Simple Business models demonstrating STI with the django-sti-models framework.
"""

from django.db import models
from django_sti_models import TypedModel, TypeField


# Mock dependencies for the example
class AugendModel(models.Model):
    """Mock AugendModel with common fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Business(TypedModel, AugendModel):
    """
    Concrete STI base model for businesses.
    
    This creates the actual database table that all subclasses will share.
    """
    model_type = TypeField()  # The STI discriminator field
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        app_label = 'examples'
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name


class BusinessExtension(Business):
    """
    STI subclass that adds fields to the shared table.
    
    This demonstrates the Salesforce-style extensibility.
    """
    cif_number = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    class Meta:
        app_label = 'examples'
        verbose_name_plural = "Business Extensions"

    def __str__(self):
        return f"{self.name} (Extended)"


class PremiumBusiness(Business):
    """Another STI subclass with different extensions."""
    premium_level = models.CharField(
        max_length=20,
        choices=[('gold', 'Gold'), ('platinum', 'Platinum')],
        default='gold'
    )
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        app_label = 'examples'

    def __str__(self):
        return f"{self.name} ({self.get_premium_level_display()})"


def test_sti():
    """Simple test function to verify STI is working."""
    # Create instances
    business = Business.objects.create(name="Acme Corp")
    extension = BusinessExtension.objects.create(name="Tech Inc", cif_number="B123")
    premium = PremiumBusiness.objects.create(name="Elite Corp", premium_level="platinum")
    
    print(f"Business: {business} (type: {business.model_type})")
    print(f"Extension: {extension} (type: {extension.model_type})")
    print(f"Premium: {premium} (type: {premium.model_type})")
    
    # Verify table sharing
    print(f"\nTable names:")
    print(f"Business: {Business._meta.db_table}")
    print(f"BusinessExtension: {BusinessExtension._meta.db_table}")
    print(f"PremiumBusiness: {PremiumBusiness._meta.db_table}")
    
    # Test querying
    all_businesses = Business.objects.all()
    extensions_only = BusinessExtension.objects.all()
    
    print(f"\nAll businesses: {all_businesses.count()}")
    print(f"Extensions only: {extensions_only.count()}")
    
    return all_businesses.count() == 3 and extensions_only.count() == 1 