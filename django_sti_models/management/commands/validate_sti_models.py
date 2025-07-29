"""
Django management command to validate STI models.
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models

from django_sti_models import TypedModel
from django_sti_models.utils import (
    get_type_statistics,
    validate_type_consistency,
    validate_type_registration,
)


class Command(BaseCommand):
    """
    Validate STI models for consistency and configuration issues.
    """

    help = "Validate STI models for consistency and configuration issues"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            type=str,
            help="Only validate models from a specific app",
        )
        parser.add_argument(
            "--model",
            type=str,
            help="Only validate a specific model",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to fix common issues automatically",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Show type statistics",
        )

    def handle(self, *args, **options):
        """Handle the command."""
        app_label = options.get("app")
        model_name = options.get("model")
        fix_issues = options.get("fix")
        show_stats = options.get("stats")

        # Find typed models
        typed_models = self._find_typed_models(app_label, model_name)

        if not typed_models:
            self.stdout.write(self.style.WARNING("No typed models found."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(typed_models)} typed model(s)")
        )

        # Validate each model
        all_errors = []
        all_warnings = []

        for model in typed_models:
            self.stdout.write(f"\nValidating {model.__name__}...")

            # Registration validation
            registration_errors = validate_type_registration(model)
            if registration_errors:
                all_errors.extend(
                    [f"{model.__name__}: {error}" for error in registration_errors]
                )
                for error in registration_errors:
                    self.stdout.write(self.style.ERROR(f"  ERROR: {error}"))

            # Consistency validation
            consistency_errors = validate_type_consistency(model)
            if consistency_errors:
                all_warnings.extend(
                    [f"{model.__name__}: {error}" for error in consistency_errors]
                )
                for error in consistency_errors:
                    self.stdout.write(self.style.WARNING(f"  WARNING: {error}"))

            # Show statistics
            if show_stats:
                stats = get_type_statistics(model)
                if stats:
                    self.stdout.write("  Type statistics:")
                    for type_name, count in stats.items():
                        self.stdout.write(f"    {type_name}: {count}")

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("VALIDATION SUMMARY")
        self.stdout.write("=" * 50)

        if all_errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(all_errors)}"))
            for error in all_errors:
                self.stdout.write(f"  {error}")
        else:
            self.stdout.write(self.style.SUCCESS("No errors found!"))

        if all_warnings:
            self.stdout.write(self.style.WARNING(f"Warnings: {len(all_warnings)}"))
            for warning in all_warnings:
                self.stdout.write(f"  {warning}")
        else:
            self.stdout.write(self.style.SUCCESS("No warnings found!"))

        # Exit with error code if there are errors
        if all_errors:
            raise CommandError(f"Validation failed with {len(all_errors)} error(s)")

    def _find_typed_models(self, app_label: str = None, model_name: str = None) -> list:
        """Find typed models in the project."""
        typed_models = []

        for app_config in apps.get_app_configs():
            if app_label and app_config.label != app_label:
                continue

            for model in app_config.get_models():
                if model_name and model.__name__ != model_name:
                    continue

                if issubclass(model, TypedModel) and not model._meta.abstract:
                    typed_models.append(model)

        return typed_models
