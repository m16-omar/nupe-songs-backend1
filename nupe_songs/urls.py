from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
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

# Serve static/media files in both development and production (if S3 is not active)
if not getattr(settings, 'USE_S3', False):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]
