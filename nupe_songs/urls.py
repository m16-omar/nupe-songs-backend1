from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api.views import (
    landing_view, admin_lyrics_view, admin_favorites_view,
    admin_analytics_view, admin_settings_view, admin_backups_view,
    admin_trash_view
)

urlpatterns = [
    path('', landing_view, name='landing'),
    path('admin/lyrics/', admin_lyrics_view, name='admin_lyrics'),
    path('admin/favorites/', admin_favorites_view, name='admin_favorites'),
    path('admin/analytics/', admin_analytics_view, name='admin_analytics'),
    path('admin/settings-page/', admin_settings_view, name='admin_settings'),
    path('admin/backups-page/', admin_backups_view, name='admin_backups'),
    path('admin/trash-page/', admin_trash_view, name='admin_trash'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# Serve static/media files locally during development (if S3 is not active)
if settings.DEBUG and not getattr(settings, 'USE_S3', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
