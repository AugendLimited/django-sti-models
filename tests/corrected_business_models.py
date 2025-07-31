from django.db import models
from django_sti_models import TypedModel, TypeField

# If you need to import AugendModel from your actual project:
# from augend.common.models import AugendModel

# Mock AugendModel for this example
class AugendModel(models.Model):
    """Mock AugendModel with common fields for this example."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Business(TypedModel, AugendModel):
    """
    Concrete STI base model - this creates the actual database table.
    All subclasses will share this same table using Django's proxy model approach.
    
    ✅ CRITICAL: This model must NOT be abstract for STI to work!
    """
    name = models.CharField(max_length=255)
    model_type = TypeField()  # The STI discriminator field

    class Meta:
        verbose_name_plural = "Businesses"
        # ✅ Do NOT set abstract = True for STI base models!

    def __str__(self):
        return self.name


class BusinessExtension(Business):
    """
    STI subclass - shares the Business table via Django's proxy model approach.
    Django will NOT create a separate table for this model.
    
    The django-sti-models framework automatically:
    1. Moves fields from subclass to base class during metaclass processing  
    2. Sets proxy=True in the metaclass
    3. Filters queries by model_type = 'BusinessExtension'
    4. Manages the type field automatically
    
    ✅ Fields on subclasses are automatically moved to the base table!
    """
    description = models.TextField(blank=True, default="")  # Will be moved to base class!
    cif_number = models.CharField(max_length=255, blank=True, default="")  # Will be moved to base class!

    class Meta:
        verbose_name_plural = "Business Extensions"
        # ✅ proxy=True is automatically set by the framework

    def __str__(self):
        return f"{self.name} (Extended)"


# Test function to verify STI is working
def test_sti_working():
    """
    Test function to verify STI is working correctly.
    Should show:
    1. Same table name for both models
    2. Type-aware querying works
    3. Automatic type field population
    """
    print("Testing STI Implementation...")
    
    # Check table sharing
    business_table = Business._meta.db_table
    extension_table = BusinessExtension._meta.db_table
    
    print(f"Business table: {business_table}")
    print(f"BusinessExtension table: {extension_table}")
    print(f"Tables match: {business_table == extension_table}")
    
    # Test creation and querying
    business = Business.objects.create(name="Acme Corp")
    extension = BusinessExtension.objects.create(name="Tech Inc", description="A tech company")
    
    print(f"\nCreated Business: {business} (type: {business.model_type})")
    print(f"Created Extension: {extension} (type: {extension.model_type})")
    
    # Test type-aware querying
    all_businesses = Business.objects.all()
    extensions_only = BusinessExtension.objects.all()
    
    print(f"\nAll businesses count: {all_businesses.count()}")
    print(f"Extensions only count: {extensions_only.count()}")
    
    return business_table == extension_table