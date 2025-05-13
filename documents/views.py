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

def user_login(request):
    """
    Handle user login with support for both username and email authentication
    """
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me') == 'on'
        
        # Пробуем найти пользователя сначала по имени
        user = authenticate(request, username=username_or_email, password=password)
        
        # Если пользователь не найден по имени, пробуем по email
        if user is None:
            try:
                # Ищем пользователя по email
                user_obj = User.objects.get(email=username_or_email)
                # Аутентифицируем по найденному username и введенному паролю
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            # Если "запомнить меня" не отмечено, сессия будет удалена при закрытии браузера
            if not remember_me:
                request.session.set_expiry(0)
            
            login(request, user)
            messages.success(request, f"Здравствуйте, {user.username}! Вы успешно вошли в систему.")
            # Редирект на страницу, с которой пришел пользователь, или на главную
            next_page = request.GET.get('next', reverse('document-list'))
            return redirect(next_page)
        else:
            messages.error(request, "Неверное имя пользователя/email или пароль.")
            # Возвращаемся на предыдущую страницу с параметром для отображения модального окна
            referer = request.META.get('HTTP_REFERER', reverse('document-list'))
            if '?' in referer:
                referer += '&show_login_modal=1'
            else:
                referer += '?show_login_modal=1'
            return redirect(referer)
    
    # GET запросы перенаправляем на главную
    return redirect('document-list')

def user_logout(request):
    """
    Handle user logout
    """
    logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect('document-list')

def user_register(request):
    """
    Handle user registration
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Проверка данных
        if password1 != password2:
            messages.error(request, "Пароли не совпадают.")
            referer = request.META.get('HTTP_REFERER', reverse('document-list'))
            if '?' in referer:
                referer += '&show_register_modal=1'
            else:
                referer += '?show_register_modal=1'
            return redirect(referer)
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Пользователь с таким именем уже существует.")
            referer = request.META.get('HTTP_REFERER', reverse('document-list'))
            if '?' in referer:
                referer += '&show_register_modal=1'
            else:
                referer += '?show_register_modal=1'
            return redirect(referer)
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Пользователь с таким email уже существует.")
            referer = request.META.get('HTTP_REFERER', reverse('document-list'))
            if '?' in referer:
                referer += '&show_register_modal=1'
            else:
                referer += '?show_register_modal=1'
            return redirect(referer)
        
        # Создание пользователя
        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()
            
            # Автоматический вход после регистрации
            login_user = authenticate(request, username=username, password=password1)
            if login_user is not None:
                login(request, login_user)
                messages.success(request, f"Здравствуйте, {username}! Ваш аккаунт успешно создан.")
            else:
                messages.success(request, "Аккаунт успешно создан. Пожалуйста, войдите в систему.")
            
            return redirect('document-list')
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            messages.error(request, f"Ошибка при создании пользователя: {str(e)}")
            return redirect(request.META.get('HTTP_REFERER', reverse('document-list')))
    
    # GET запросы перенаправляем на главную
    return redirect('document-list')

def reset_password_request(request):
    """
    Handle password reset request
    
    Примечание: В текущей реализации письма не отправляются. 
    Для полной функциональности необходимо настроить SMTP-сервер
    и использовать Django Password Reset Views.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if User.objects.filter(email=email).exists():
            # TODO: Реализовать отправку email со ссылкой для сброса пароля
            # Для этого необходимо использовать Django Password Reset Views
            # и настроить параметры EMAIL_* в settings.py
            messages.info(request, "Инструкции по сбросу пароля отправлены на ваш email. (Функция в разработке)")
        else:
            # Для безопасности не сообщаем, что пользователя с таким email не существует
            messages.info(request, "Инструкции по сбросу пароля отправлены на ваш email (если он зарегистрирован). (Функция в разработке)")
        
        return redirect('document-list')
    
    # GET запросы перенаправляем на главную
    return redirect('document-list')
