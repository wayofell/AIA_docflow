from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='document')

# URL patterns for the Documents app
urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Frontend pages
    path('', views.home_page, name='home'),
    path('documents/', views.document_list_page, name='document-list'),
    path('documents/upload/', views.document_upload_page, name='document-upload'),
    path('documents/<int:pk>/', views.document_view_page, name='document-view'),
    path('documents/search/', views.search_page, name='document-search'),
    
    # Authentication URLs
    path('login/', views.user_login, name='user-login'),
    path('logout/', views.user_logout, name='user-logout'),
    path('register/', views.user_register, name='user-register'),
    path('reset-password/', views.reset_password_request, name='reset-password'),
] 