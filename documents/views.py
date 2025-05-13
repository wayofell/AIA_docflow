from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Document
from .serializers import DocumentSerializer
import logging
from django.http import FileResponse, HttpResponse
import os
import mimetypes

# Настройка логирования
logger = logging.getLogger(__name__)

class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing documents
    """
    serializer_class = DocumentSerializer
    queryset = Document.objects.all().order_by('-upload_date')
    
    def create(self, request, *args, **kwargs):
        """
        Custom create method with better error handling
        """
        logger.debug(f"Document create request: {request.data}")
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download document with proper content type
        """
        document = self.get_object()
        file_path = document.file.path
        
        if not os.path.exists(file_path):
            return Response(
                {"error": "Файл не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Определяем MIME-тип файла
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None:
            if document.file_format == 'pdf':
                content_type = 'application/pdf'
            elif document.file_format in ['jpg', 'jpeg']:
                content_type = 'image/jpeg'
            else:
                content_type = 'application/octet-stream'
        
        # Имя файла для загрузки
        filename = os.path.basename(document.file.name)
        
        # Создаем FileResponse с правильными заголовками
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=False,  # Просмотр в браузере вместо загрузки
            filename=filename
        )
        
        # Добавляем заголовки безопасности
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        # Специальные заголовки для PDF
        if document.file_format == 'pdf':
            response['Accept-Ranges'] = 'bytes'
        
        return response
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search documents by title or content
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {"error": "Search query is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search in both title and text_content
        documents = Document.objects.filter(
            Q(title__icontains=query) | Q(text_content__icontains=query)
        ).order_by('-upload_date')
        
        page = self.paginate_queryset(documents)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)

def home_page(request):
    """
    Redirect to document list page
    """
    return redirect('document-list')

def document_upload_page(request):
    """
    Render the document upload page
    """
    return render(request, 'documents/upload.html')

def document_list_page(request):
    """
    Render the document list page
    """
    return render(request, 'documents/list.html')

def document_view_page(request, pk):
    """
    Render the document view page
    """
    return render(request, 'documents/view.html', {'document_id': pk})

def search_page(request):
    """
    Render the search page
    """
    return render(request, 'documents/search.html')

def document_file_view(request, pk):
    """
    Serve document file directly with proper content type
    """
    document = get_object_or_404(Document, pk=pk)
    file_path = document.file.path
    
    # Определяем MIME-тип файла
    content_type, encoding = mimetypes.guess_type(file_path)
    if content_type is None:
        if document.file_format == 'pdf':
            content_type = 'application/pdf'
        elif document.file_format in ['jpg', 'jpeg']:
            content_type = 'image/jpeg'
        else:
            content_type = 'application/octet-stream'
    
    # Открываем файл и создаем HTTP-ответ
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
            
        response = HttpResponse(file_data, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(document.file.name)}"'
        return response
    except IOError:
        logger.error(f"Error opening document file: {file_path}")
        return HttpResponse("Ошибка при чтении файла", status=404)
