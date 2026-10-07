"""
DentFlow — Root URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

@require_http_methods(["GET"])
def api_root(request):
    """API root endpoint — service info"""
    return JsonResponse({
        "service": "DentFlow API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/api/docs/",
            "redoc": "/api/redoc/",
            "schema": "/api/schema/",
            "admin": "/admin/",
            "auth": {
                "login": "/api/auth/login/",
                "refresh": "/api/auth/refresh/",
            },
            "resources": {
                "doctors": "/api/doctors/",
                "services": "/api/services/",
                "patients": "/api/patients/",
                "appointments": "/api/appointments/",
                "stats": "/api/stats/dashboard/",
            }
        }
    })

@require_http_methods(["GET"])
def root_redirect(request):
    """Root sahifadan Swagger UI ga yo'naltirish"""
    return HttpResponseRedirect('/api/docs/')

@require_http_methods(["GET"])
def favicon_view(request):
    """Empty favicon to prevent 404 errors"""
    return HttpResponse(status=204)

urlpatterns = [
    # Root - Swagger UI ga redirect
    path('', root_redirect, name='root'),

    path('admin/', admin.site.urls),

    # API Root Info
    path('api/', api_root, name='api-root'),

    # Favicon
    path('favicon.ico', favicon_view),

    # Auth
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API Documentation (Swagger / Redoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),


    # Main API
    path('api/', include('clinic.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
