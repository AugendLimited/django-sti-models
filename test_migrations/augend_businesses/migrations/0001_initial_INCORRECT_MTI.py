# Generated by Django 5.2.4 on 2025-07-31 15:20

import django.db.models.deletion
import django_sti_models.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('model_type', django_sti_models.fields.TypeField(choices=[], db_index=True, editable=False, max_length=100)),
                ('name', models.CharField(max_length=255)),
                ('created_by', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='created_%(class)ss', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='updated_%(class)ss', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Businesses',
            },
        ),
        migrations.CreateModel(
            name='BusinessExtension',  # PROBLEM: Separate table created
            fields=[
                ('business_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='augend_businesses.business')),
                ('description', models.TextField(blank=True, default='')),  # MTI: Extension field in separate table
            ],
            options={
                'verbose_name_plural': 'Business Extensions',
            },
            bases=('augend_businesses.business',),  # MTI inheritance
        ),
    ]
