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
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse

# Настройка логирования
logger = logging.getLogger(__name__)

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.owner == request.user

class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing documents
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """
        This view should return a list of all documents
        for the currently authenticated user.
        """
        user = self.request.user
        return Document.objects.filter(owner=user).order_by('-upload_date')
    
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
            # Явное определение MIME-типов для известных форматов
            if document.file_format == 'pdf':
                content_type = 'application/pdf'
            elif document.file_format in ['jpg', 'jpeg']:
                content_type = 'image/jpeg'
            elif document.file_format == 'png':
                content_type = 'image/png'
            elif document.file_format == 'gif':
                content_type = 'image/gif'
            elif document.file_format == 'svg':
                content_type = 'image/svg+xml'
            elif document.file_format == 'heic':
                content_type = 'image/heic'
            elif document.file_format == 'doc':
                content_type = 'application/msword'
            elif document.file_format == 'docx':
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif document.file_format == 'xls':
                content_type = 'application/vnd.ms-excel'
            elif document.file_format == 'xlsx':
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif document.file_format == 'ppt':
                content_type = 'application/vnd.ms-powerpoint'
            elif document.file_format == 'pptx':
                content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            elif document.file_format == 'txt':
                content_type = 'text/plain'
            elif document.file_format == 'md':
                content_type = 'text/markdown'
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
        
        # Search in both title and text_content, only for user's documents
        documents = Document.objects.filter(
            Q(title__icontains=query) | Q(text_content__icontains=query),
            owner=request.user
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
    if not request.user.is_authenticated:
        return redirect(f"{reverse('document-list')}?show_login_modal=1")
        
    context = {
        'show_login_modal': 'show_login_modal' in request.GET,
        'show_register_modal': 'show_register_modal' in request.GET
    }
    return render(request, 'documents/upload.html', context)

def document_list_page(request):
    """
    Render the document list page
    """
    context = {
        'show_login_modal': 'show_login_modal' in request.GET,
        'show_register_modal': 'show_register_modal' in request.GET
    }
    return render(request, 'documents/list.html', context)

def document_view_page(request, pk):
    """
    Render the document view page
    """
    document = get_object_or_404(Document, pk=pk)
    
    # Check if the user is the owner of the document
    if not request.user.is_authenticated or document.owner != request.user:
        return redirect(f"{reverse('document-list')}?show_login_modal=1")
        
    context = {
        'document_id': pk,
        'show_login_modal': 'show_login_modal' in request.GET,
        'show_register_modal': 'show_register_modal' in request.GET
    }
    return render(request, 'documents/view.html', context)

def search_page(request):
    """
    Render the search page
    """
    if not request.user.is_authenticated:
        return redirect(f"{reverse('document-list')}?show_login_modal=1")
        
    context = {
        'show_login_modal': 'show_login_modal' in request.GET,
        'show_register_modal': 'show_register_modal' in request.GET
    }
    return render(request, 'documents/search.html', context)

def document_file_view(request, pk):
    """
    Serve document file directly with proper content type
    """
    document = get_object_or_404(Document, pk=pk)
    
    # Check if the user is the owner of the document
    if not request.user.is_authenticated or document.owner != request.user:
        return redirect(f"{reverse('document-list')}?show_login_modal=1")
        
    file_path = document.file.path
    
    # Определяем MIME-тип файла
    content_type, encoding = mimetypes.guess_type(file_path)
    if content_type is None:
        # Явное определение MIME-типов для известных форматов
        if document.file_format == 'pdf':
            content_type = 'application/pdf'
        elif document.file_format in ['jpg', 'jpeg']:
            content_type = 'image/jpeg'
        elif document.file_format == 'png':
            content_type = 'image/png'
        elif document.file_format == 'gif':
            content_type = 'image/gif'
        elif document.file_format == 'svg':
            content_type = 'image/svg+xml'
        elif document.file_format == 'heic':
            content_type = 'image/heic'
        elif document.file_format == 'doc':
            content_type = 'application/msword'
        elif document.file_format == 'docx':
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif document.file_format == 'xls':
            content_type = 'application/vnd.ms-excel'
        elif document.file_format == 'xlsx':
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif document.file_format == 'ppt':
            content_type = 'application/vnd.ms-powerpoint'
        elif document.file_format == 'pptx':
            content_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        elif document.file_format == 'txt':
            content_type = 'text/plain'
        elif document.file_format == 'md':
            content_type = 'text/markdown'
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

def user_login(request):
    """
    Handle user login with support for both username and email authentication
    """
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me') == 'on'
        
        # Check if user exists with this username or email
        user = None
        try:
            # First try to authenticate with username
            user = authenticate(username=username_or_email, password=password)
            
            # If that fails, try with email
            if user is None:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
        
        if user is not None:
            login(request, user)
            
            # Set session expiry based on remember_me
            if not remember_me:
                request.session.set_expiry(0)  # Session expires when browser closes
            
            messages.success(request, f"Успешный вход в систему. Добро пожаловать, {user.username}!")
            
            # Redirect to the page where login was initiated
            next_url = request.POST.get('next', 'document-list')
            return redirect(next_url)
        else:
            messages.error(request, "Неправильное имя пользователя/email или пароль.")
            
            # Redirect back with error message and show login modal
            return redirect(f"{reverse('document-list')}?show_login_modal=1")
    else:
        # GET request is not handled here, redirecting to the main page
        return redirect('document-list')

def user_logout(request):
    """
    Handle user logout
    """
    logout(request)
    messages.success(request, "Вы успешно вышли из системы.")
    return redirect('document-list')

def user_register(request):
    """
    Handle user registration
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Basic validation
        if not (username and email and password and password_confirm):
            messages.error(request, "Все поля обязательны для заполнения.")
            return redirect(f"{reverse('document-list')}?show_register_modal=1")
            
        if password != password_confirm:
            messages.error(request, "Пароли не совпадают.")
            return redirect(f"{reverse('document-list')}?show_register_modal=1")
            
        if len(password) < 8:
            messages.error(request, "Пароль должен быть не менее 8 символов.")
            return redirect(f"{reverse('document-list')}?show_register_modal=1")
        
        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Пользователь с таким именем уже существует.")
            return redirect(f"{reverse('document-list')}?show_register_modal=1")
            
        if User.objects.filter(email=email).exists():
            messages.error(request, "Пользователь с таким email уже существует.")
            return redirect(f"{reverse('document-list')}?show_register_modal=1")
        
        # Create the user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Auto-login after registration
            login(request, user)
            messages.success(request, f"Регистрация успешна. Добро пожаловать, {username}!")
            return redirect('document-list')
        except Exception as e:
            logger.error(f"Error during user registration: {str(e)}")
            messages.error(request, f"Ошибка при регистрации: {str(e)}")
            return redirect(f"{reverse('document-list')}?show_register_modal=1")
    else:
        # GET request is not handled here, redirecting to the main page
        return redirect('document-list')

def reset_password_request(request):
    """
    Handle password reset request
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Validate email
        if not email:
            messages.error(request, "Укажите email.")
            return redirect(f"{reverse('document-list')}?show_reset_modal=1")
        
        # Check if user with this email exists
        try:
            user = User.objects.get(email=email)
            
            # Here should be code to send email with password reset link
            # For demo, just set a simple password
            new_password = "temp1234"
            user.set_password(new_password)
            user.save()
            
            messages.success(request, f"Пароль сброшен. Новый пароль: {new_password}")
            return redirect(f"{reverse('document-list')}?show_login_modal=1")
        except User.DoesNotExist:
            messages.error(request, "Пользователь с таким email не найден.")
            return redirect(f"{reverse('document-list')}?show_reset_modal=1")
        except Exception as e:
            logger.error(f"Error during password reset: {str(e)}")
            messages.error(request, f"Ошибка при сбросе пароля: {str(e)}")
            return redirect(f"{reverse('document-list')}?show_reset_modal=1")
    else:
        # GET request is not handled here, redirecting to the main page
        return redirect('document-list')
