from rest_framework import serializers
from .models import Document
import os
import logging
from .utils import extract_text_from_file

# Настройка логирования
logger = logging.getLogger(__name__)

class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for Document model
    """
    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'file_format', 'upload_date', 'size', 'text_content']
        read_only_fields = ['id', 'upload_date', 'size', 'text_content']

    def validate_file(self, file):
        """
        Validate that the file has an allowed format
        """
        # Проверка на наличие файла
        if not file:
            raise serializers.ValidationError("Файл не предоставлен")
            
        # Get the file extension
        file_name = file.name
        logger.debug(f"Validating file: {file_name}, size: {file.size}")
        
        ext = os.path.splitext(file_name)[1].lower().replace('.', '')
        
        # Check if the extension is in allowed formats
        allowed_formats = [Document.PDF, Document.JPG, Document.JPEG]
        if ext not in allowed_formats:
            error_msg = f"Неподдерживаемый формат файла. Разрешенные форматы: {', '.join(allowed_formats)}"
            logger.error(error_msg)
            raise serializers.ValidationError(error_msg)
        
        # Check file size (max 10MB)
        if file.size > 10 * 1024 * 1024:  # 10MB
            error_msg = "Размер файла превышает максимально допустимый (10MB)"
            logger.error(error_msg)
            raise serializers.ValidationError(error_msg)
            
        return file
    
    def validate(self, attrs):
        """
        Validate all attributes
        """
        # Проверка на наличие заголовка
        if not attrs.get('title'):
            raise serializers.ValidationError({"title": "Укажите название документа"})
            
        return attrs
    
    def create(self, validated_data):
        """
        Create document instance and extract text from file
        """
        try:
            # Set file_format based on file extension
            file = validated_data['file']
            ext = os.path.splitext(file.name)[1].lower().replace('.', '')
            validated_data['file_format'] = ext
            
            # Create the document instance
            document = Document.objects.create(**validated_data)
            
            # Extract text from file
            logger.info(f"Extracting text from file: {document.file.path}")
            text_content = extract_text_from_file(document.file.path)
            document.text_content = text_content
            document.save(update_fields=['text_content'])
            
            return document
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            raise serializers.ValidationError(f"Ошибка при создании документа: {str(e)}") 