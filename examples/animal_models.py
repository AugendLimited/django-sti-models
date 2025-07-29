"""
Example demonstrating Django STI Models with animal hierarchy.
"""

from django.db import models

from django_sti_models import TypedModel, TypeField


class Animal(TypedModel):
    """
    Base animal model demonstrating Single Table Inheritance.

    All animals have common fields like name and age, but different
    subtypes can have their own specific fields and behaviors.
    """

    name = models.CharField(max_length=100)
    age = models.IntegerField()
    weight = models.FloatField()
    animal_type = TypeField()  # More descriptive than just 'type'

    class Meta:
        abstract = True

    def make_sound(self):
        """Base method that should be overridden by subtypes."""
        return f"{self.name} makes a sound"

    def get_info(self):
        """Get basic information about the animal."""
        return f"{self.name} is {self.age} years old and weighs {self.weight}kg"


class Dog(Animal):
    """Dog subtype with breed-specific fields and behaviors."""

    breed = models.CharField(max_length=50)
    is_good_boy = models.BooleanField(default=True)

    def make_sound(self):
        """Dogs bark."""
        return f"{self.name} says woof!"

    def fetch(self, item):
        """Dogs can fetch items."""
        return f"{self.name} fetches the {item}"

    def get_info(self):
        """Get detailed information about the dog."""
        base_info = super().get_info()
        return f"{base_info}. Breed: {self.breed}. Good boy: {self.is_good_boy}"


class Cat(Animal):
    """Cat subtype with cat-specific fields and behaviors."""

    color = models.CharField(max_length=30)
    is_independent = models.BooleanField(default=True)

    def make_sound(self):
        """Cats meow."""
        return f"{self.name} says meow!"

    def purr(self):
        """Cats can purr."""
        return f"{self.name} purrs contentedly"

    def get_info(self):
        """Get detailed information about the cat."""
        base_info = super().get_info()
        return f"{base_info}. Color: {self.color}. Independent: {self.is_independent}"


class Bird(Animal):
    """Bird subtype with bird-specific fields and behaviors."""

    wingspan = models.FloatField()
    can_fly = models.BooleanField(default=True)

    def make_sound(self):
        """Birds chirp."""
        return f"{self.name} says tweet!"

    def fly(self):
        """Birds can fly (if they can)."""
        if self.can_fly:
            return f"{self.name} flies gracefully"
        else:
            return f"{self.name} tries to fly but can't"

    def get_info(self):
        """Get detailed information about the bird."""
        base_info = super().get_info()
        return f"{base_info}. Wingspan: {self.wingspan}cm. Can fly: {self.can_fly}"


class Fish(Animal):
    """Fish subtype with fish-specific fields and behaviors."""

    species = models.CharField(max_length=50)
    water_type = models.CharField(
        max_length=20,
        choices=[
            ("fresh", "Freshwater"),
            ("salt", "Saltwater"),
            ("brackish", "Brackish"),
        ],
    )

    def make_sound(self):
        """Fish are generally quiet."""
        return f"{self.name} bubbles quietly"

    def swim(self):
        """Fish can swim."""
        return f"{self.name} swims in {self.water_type} water"

    def get_info(self):
        """Get detailed information about the fish."""
        base_info = super().get_info()
        return f"{base_info}. Species: {self.species}. Water type: {self.water_type}"


# Example usage functions
def create_sample_animals():
    """Create sample animals of different types."""
    animals = []

    # Create a dog
    dog = Dog.objects.create(
        name="Rex", age=3, weight=25.5, breed="Golden Retriever", is_good_boy=True
    )
    animals.append(dog)

    # Create a cat
    cat = Cat.objects.create(
        name="Whiskers", age=2, weight=4.2, color="Orange", is_independent=True
    )
    animals.append(cat)

    # Create a bird
    bird = Bird.objects.create(
        name="Tweety", age=1, weight=0.1, wingspan=12.5, can_fly=True
    )
    animals.append(bird)

    # Create a fish
    fish = Fish.objects.create(
        name="Nemo", age=1, weight=0.05, species="Clownfish", water_type="salt"
    )
    animals.append(fish)

    return animals


def demonstrate_typed_queries():
    """Demonstrate different types of queries with typed models."""
    print("=== Typed Model Query Examples ===\n")

    # Create sample data
    animals = create_sample_animals()

    # Query all animals
    print("All animals:")
    all_animals = Animal.objects.all()
    for animal in all_animals:
        print(f"  - {animal.get_info()}")
    print()

    # Query specific types
    print("Dogs only:")
    dogs = Dog.objects.all()
    for dog in dogs:
        print(f"  - {dog.get_info()}")
        print(f"    Sound: {dog.make_sound()}")
        print(f"    Fetch: {dog.fetch('ball')}")
    print()

    print("Cats only:")
    cats = Cat.objects.all()
    for cat in cats:
        print(f"  - {cat.get_info()}")
        print(f"    Sound: {cat.make_sound()}")
        print(f"    Purr: {cat.purr()}")
    print()

    print("Birds only:")
    birds = Bird.objects.all()
    for bird in birds:
        print(f"  - {bird.get_info()}")
        print(f"    Sound: {bird.make_sound()}")
        print(f"    Fly: {bird.fly()}")
    print()

    print("Fish only:")
    fish = Fish.objects.all()
    for fish in fish:
        print(f"  - {fish.get_info()}")
        print(f"    Sound: {fish.make_sound()}")
        print(f"    Swim: {fish.swim()}")
    print()

    # Demonstrate type registration
    print("Registered types:")
    registered_types = Animal.get_all_types()
    for type_name, type_class in registered_types.items():
        print(f"  - {type_name}: {type_class}")
    print()

    # Demonstrate getting real instances
    print("Getting real instances:")
    for animal in Animal.objects.all():
        real_animal = animal.get_real_instance()
        print(f"  - {animal.name} is actually a {real_animal.__class__.__name__}")
        print(f"    Sound: {real_animal.make_sound()}")


if __name__ == "__main__":
    # This would be run in a Django shell or management command
    demonstrate_typed_queries()
