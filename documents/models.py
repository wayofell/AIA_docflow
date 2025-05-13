from django.db import models
import os
from django.utils import timezone
from django.contrib.auth.models import User

def document_upload_path(instance, filename):
    # Generate path like: documents/YYYY/MM/DD/filename
    today = timezone.now()
    return f'documents/{today.year}/{today.month}/{today.day}/{filename}'

class Document(models.Model):
    """
    Model to store document information and files.
    """
    # File formats supported according to the technical task
    PDF = 'pdf'
    JPG = 'jpg'
    JPEG = 'jpeg'
    PNG = 'png'
    GIF = 'gif'
    HEIC = 'heic'
    SVG = 'svg'
    DOC = 'doc'
    DOCX = 'docx'
    PPT = 'ppt'
    PPTX = 'pptx'
    TXT = 'txt'
    XLS = 'xls'
    XLSX = 'xlsx'
    MD = 'md'
    
    FORMAT_CHOICES = [
        (PDF, 'PDF'),
        (JPG, 'JPG'),
        (JPEG, 'JPEG'),
        (PNG, 'PNG'),
        (GIF, 'GIF'),
        (HEIC, 'HEIC'),
        (SVG, 'SVG'),
        (DOC, 'DOC'),
        (DOCX, 'DOCX'),
        (PPT, 'PPT'),
        (PPTX, 'PPTX'),
        (TXT, 'TXT'),
        (XLS, 'XLS'),
        (XLSX, 'XLSX'),
        (MD, 'MD'),
    ]
    
    title = models.CharField(max_length=255, verbose_name="Document title")
    file = models.FileField(upload_to=document_upload_path, verbose_name="Document file")
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, verbose_name="File format", blank=True, null=True)
    text_content = models.TextField(blank=True, verbose_name="Extracted text content")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents', verbose_name="Document owner", null=True)
    
    # Metadata
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="Upload date")
    size = models.PositiveIntegerField(verbose_name="File size (bytes)")
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # If this is a new document, calculate its size
        if not self.pk:
            self.size = self.file.size
            
            # Determine file format from extension if not set
            if not self.file_format and self.file:
                ext = os.path.splitext(self.file.name)[1].lower().replace('.', '')
                valid_formats = [self.PDF, self.JPG, self.JPEG, self.PNG, self.GIF, self.HEIC, 
                                self.SVG, self.DOC, self.DOCX, self.PPT, self.PPTX, self.TXT,
                                self.XLS, self.XLSX, self.MD]
                if ext in valid_formats:
                    self.file_format = ext
                    
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Delete the file when deleting the document
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)
