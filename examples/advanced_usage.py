"""
Advanced usage examples for Django STI Models.

This example demonstrates advanced features and best practices for using
the Django STI Models library.
"""

from django.contrib import admin
from django.db import models

from django_sti_models import (
    TypedModel,
    TypedModelAdmin,
    TypeField,
    create_typed_instance,
    filter_by_type,
    get_type_statistics,
    register_typed_models,
    validate_type_consistency,
)

# ============================================================================
# Advanced Model Examples
# ============================================================================


class Content(TypedModel):
    """
    Base content model with advanced features.

    This demonstrates:
    - Custom type field name
    - Advanced validation
    - Polymorphic methods
    """

    title = models.CharField(max_length=200)
    content_type = TypeField(max_length=50)  # Custom field name
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.content_type})"

    def get_display_name(self) -> str:
        """Get a display name for the content."""
        return self.title

    def can_be_published(self) -> bool:
        """Check if content can be published."""
        return True

    def publish(self) -> bool:
        """Publish the content."""
        if self.can_be_published():
            self.is_published = True
            self.save(update_fields=["is_published"])
            return True
        return False


class Article(Content):
    """Article content type."""

    body = models.TextField()
    author = models.CharField(max_length=100)
    tags = models.CharField(max_length=500, blank=True)

    def get_display_name(self) -> str:
        return f"Article: {self.title} by {self.author}"

    def can_be_published(self) -> bool:
        return bool(self.body and self.author)


class Video(Content):
    """Video content type."""

    video_url = models.URLField()
    duration = models.IntegerField(help_text="Duration in seconds")
    thumbnail_url = models.URLField(blank=True)

    def get_display_name(self) -> str:
        return f"Video: {self.title} ({self.duration}s)"

    def can_be_published(self) -> bool:
        return bool(self.video_url and self.duration > 0)


class Podcast(Content):
    """Podcast content type."""

    audio_url = models.URLField()
    duration = models.IntegerField(help_text="Duration in seconds")
    transcript = models.TextField(blank=True)
    host = models.CharField(max_length=100)

    def get_display_name(self) -> str:
        return f"Podcast: {self.title} with {self.host}"

    def can_be_published(self) -> bool:
        return bool(self.audio_url and self.host)


# ============================================================================
# Vehicle Example with Different Naming Pattern
# ============================================================================


class Vehicle(TypedModel):
    """
    Vehicle model demonstrating another naming pattern.

    This shows how you can use different descriptive names
    for the type field based on your domain.
    """

    name = models.CharField(max_length=100)
    year = models.IntegerField()
    vehicle_kind = TypeField()  # Another descriptive name

    class Meta:
        abstract = True

    def get_info(self) -> str:
        return f"{self.name} ({self.year})"


class Car(Vehicle):
    """Car vehicle type."""

    doors = models.IntegerField()
    fuel_type = models.CharField(max_length=20)

    def get_info(self) -> str:
        base_info = super().get_info()
        return f"{base_info} - {self.doors} doors, {self.fuel_type}"


class Motorcycle(Vehicle):
    """Motorcycle vehicle type."""

    engine_size = models.FloatField()
    has_sidecar = models.BooleanField(default=False)

    def get_info(self) -> str:
        base_info = super().get_info()
        return f"{base_info} - {self.engine_size}cc engine"


# ============================================================================
# Admin Integration Examples
# ============================================================================


class ContentAdmin(TypedModelAdmin):
    """Admin for content models."""

    list_display = ["title", "content_type", "author", "is_published", "created_at"]
    list_filter = ["content_type", "is_published", "created_at"]
    search_fields = ["title", "author"]
    readonly_fields = ["content_type", "created_at", "updated_at"]

    def author(self, obj):
        """Get author information."""
        if hasattr(obj, "author"):
            return obj.author
        elif hasattr(obj, "host"):
            return obj.host
        return "N/A"

    author.short_description = "Author/Host"


# Register all content types with admin
register_typed_models(Content)


# ============================================================================
# Advanced Usage Examples
# ============================================================================


def demonstrate_advanced_features():
    """Demonstrate advanced features of the STI models."""

    print("=== Advanced STI Models Features ===\n")

    # Create sample content
    article = Article.objects.create(
        title="Getting Started with Django STI",
        body="This is a comprehensive guide...",
        author="John Doe",
        tags="django,sti,models",
    )

    video = Video.objects.create(
        title="Django STI Tutorial",
        video_url="https://example.com/video.mp4",
        duration=1200,
        thumbnail_url="https://example.com/thumb.jpg",
    )

    podcast = Podcast.objects.create(
        title="Django STI Deep Dive",
        audio_url="https://example.com/podcast.mp3",
        duration=3600,
        host="Jane Smith",
        transcript="Welcome to our podcast...",
    )

    print("Created sample content:")
    print(f"  - {article}")
    print(f"  - {video}")
    print(f"  - {podcast}\n")

    # Demonstrate type-aware queries
    print("Type-aware queries:")
    articles = Article.objects.all()
    videos = Video.objects.all()
    podcasts = Podcast.objects.all()

    print(f"  Articles: {articles.count()}")
    print(f"  Videos: {videos.count()}")
    print(f"  Podcasts: {podcasts.count()}\n")

    # Demonstrate filtering by type
    print("Filtering by type:")
    published_content = Content.objects.filter(is_published=True)
    print(f"  Published content: {published_content.count()}")

    # Use utility functions
    video_content = filter_by_type(Content.objects.all(), "Video")
    print(f"  Video content (via utility): {video_content.count()}\n")

    # Demonstrate type statistics
    print("Type statistics:")
    stats = get_type_statistics(Content)
    for content_type, count in stats.items():
        print(f"  {content_type}: {count}")
    print()

    # Demonstrate validation
    print("Validation:")
    errors = validate_type_consistency(Content)
    if errors:
        print("  Validation errors:")
        for error in errors:
            print(f"    - {error}")
    else:
        print("  No validation errors found!")
    print()

    # Demonstrate polymorphic behavior
    print("Polymorphic behavior:")
    for content in Content.objects.all():
        print(f"  {content.get_display_name()}")
        print(f"    Can be published: {content.can_be_published()}")
        if content.publish():
            print(f"    Published successfully!")
        print()

    # Demonstrate type creation by name
    print("Creating content by type name:")
    new_article = create_typed_instance(
        Content,
        "Article",
        title="Dynamic Article",
        body="Created dynamically...",
        author="Dynamic Author",
    )
    print(f"  Created: {new_article}")


def demonstrate_field_naming_patterns():
    """Demonstrate different field naming patterns."""

    print("=== Field Naming Patterns ===\n")

    print("Good field naming patterns:")
    print("  - animal_type (for Animal models)")
    print("  - content_type (for Content models)")
    print("  - vehicle_kind (for Vehicle models)")
    print("  - user_role (for User models)")
    print("  - product_category (for Product models)")
    print()

    print("Avoid using:")
    print("  - type (Python reserved word)")
    print("  - kind (too generic)")
    print("  - category (too generic)")
    print()

    print("Benefits of descriptive names:")
    print("  - Clearer code intent")
    print("  - Better IDE support")
    print("  - Avoids Python reserved word conflicts")
    print("  - More maintainable code")


def demonstrate_admin_features():
    """Demonstrate admin integration features."""

    print("=== Admin Integration Features ===\n")

    # Show how admin classes work
    print("Admin classes provide:")
    print("  - Type-aware filtering")
    print("  - Automatic type field handling")
    print("  - Validation tools")
    print("  - Statistics display")
    print()

    # Demonstrate admin registration
    print("Admin registration:")
    print("  - All content types automatically registered")
    print("  - Type-specific admin classes created")
    print("  - Consistent interface across all types")


def demonstrate_best_practices():
    """Demonstrate best practices for using STI models."""

    print("=== Best Practices ===\n")

    print("1. Use descriptive type field names:")
    print("   - animal_type, content_type, vehicle_kind")
    print("   - Avoid generic names like 'type' or 'kind'")
    print("   - Make it clear what the field represents")
    print()

    print("2. Implement polymorphic methods:")
    print("   - Override methods in subclasses")
    print("   - Use common interfaces")
    print("   - Provide sensible defaults")
    print()

    print("3. Validate type consistency:")
    print("   - Use management commands")
    print("   - Check for orphaned records")
    print("   - Validate type field values")
    print()

    print("4. Use type-aware queries:")
    print("   - Query specific types directly")
    print("   - Use utility functions for filtering")
    print("   - Leverage type statistics")
    print()

    print("5. Admin integration:")
    print("   - Use TypedModelAdmin base class")
    print("   - Register all types automatically")
    print("   - Provide type-specific customization")


if __name__ == "__main__":
    # This would be run in a Django shell or management command
    demonstrate_advanced_features()
    demonstrate_field_naming_patterns()
    demonstrate_admin_features()
    demonstrate_best_practices()
