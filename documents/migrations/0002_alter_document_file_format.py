# Generated by Django 5.2.1 on 2025-05-13 09:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='file_format',
            field=models.CharField(blank=True, choices=[('pdf', 'PDF'), ('jpg', 'JPG'), ('jpeg', 'JPEG')], max_length=10, null=True, verbose_name='File format'),
        ),
    ]
