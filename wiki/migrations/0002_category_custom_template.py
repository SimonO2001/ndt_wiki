# Generated by Django 5.1.7 on 2025-03-21 08:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wiki', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='custom_template',
            field=models.CharField(blank=True, help_text="Optional path to a custom template, e.g. 'wiki/category_production.html'", max_length=255, null=True),
        ),
    ]
