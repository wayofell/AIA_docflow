# Generated by Django 5.2.1 on 2025-05-13 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0002_alter_document_file_format'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='file_format',
            field=models.CharField(blank=True, choices=[('pdf', 'PDF'), ('jpg', 'JPG'), ('jpeg', 'JPEG'), ('png', 'PNG'), ('gif', 'GIF'), ('heic', 'HEIC'), ('svg', 'SVG'), ('doc', 'DOC'), ('docx', 'DOCX'), ('ppt', 'PPT'), ('pptx', 'PPTX'), ('txt', 'TXT'), ('xls', 'XLS'), ('xlsx', 'XLSX'), ('md', 'MD')], max_length=10, null=True, verbose_name='File format'),
        ),
    ]
