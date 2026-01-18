"""
URL configuration for contratos project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from gestion.views import auth_custom

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_custom.login_with_license, name='login'),
    path('login-cliente/', auth_custom.login_with_license, name='login_cliente'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('gestion.urls')),
]

# Servir archivos estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)