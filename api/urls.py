from django.urls import re_path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterView, UserMeView,
    ArtistViewSet, AlbumViewSet,
    SongViewSet, PlaylistViewSet,
    AdminStatsView, AdminGenreViewSet,
    AdminArtistViewSet, AdminAlbumViewSet,
    AdminSongViewSet, AdminUserViewSet,
    AdminBannerViewSet, AdminFAQViewSet,
    AdminSubscriptionViewSet, AdminDownloadViewSet,
    AdminListeningHistoryViewSet, AdminFavoriteView,
    AdminActivityLogViewSet, AdminSettingsView,
    AdminBackupView, AdminTrashView,
    AdminTrashRestoreView, AdminTrashPurgeView,
    load_fixtures_view
)

class OptionalSlashRouter(DefaultRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = '/?'

router = OptionalSlashRouter()

# Public viewsets
router.register(r'songs', SongViewSet, basename='song')
router.register(r'albums', AlbumViewSet, basename='album')
router.register(r'artists', ArtistViewSet, basename='artist')
router.register(r'playlists', PlaylistViewSet, basename='playlist')

# Admin viewsets
router.register(r'admin/genres', AdminGenreViewSet, basename='admin-genre')
router.register(r'admin/artists', AdminArtistViewSet, basename='admin-artist')
router.register(r'admin/albums', AdminAlbumViewSet, basename='admin-album')
router.register(r'admin/songs', AdminSongViewSet, basename='admin-song')
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')
router.register(r'admin/banners', AdminBannerViewSet, basename='admin-banner')
router.register(r'admin/faqs', AdminFAQViewSet, basename='admin-faq')
router.register(r'admin/subscriptions', AdminSubscriptionViewSet, basename='admin-subscription')
router.register(r'admin/downloads', AdminDownloadViewSet, basename='admin-download')
router.register(r'admin/listening-history', AdminListeningHistoryViewSet, basename='admin-listening-history')
router.register(r'admin/activity-logs', AdminActivityLogViewSet, basename='admin-activity-log')

urlpatterns = [
    # Auth Endpoints (regex for optional trailing slash)
    re_path(r'^auth/register/?$', RegisterView.as_view(), name='auth_register'),
    re_path(r'^auth/login/?$', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    re_path(r'^auth/token/refresh/?$', TokenRefreshView.as_view(), name='token_refresh'),
    re_path(r'^auth/me/?$', UserMeView.as_view(), name='auth_me'),

    # Admin Special API Views
    re_path(r'^admin/stats/?$', AdminStatsView.as_view(), name='admin_stats'),
    re_path(r'^admin/settings/?$', AdminSettingsView.as_view(), name='admin_settings'),
    re_path(r'^admin/backups/?$', AdminBackupView.as_view(), name='admin_backups'),
    re_path(r'^admin/favorites/?$', AdminFavoriteView.as_view(), name='admin_favorites'),
    re_path(r'^admin/trash/?$', AdminTrashView.as_view(), name='admin_trash'),
    re_path(r'^admin/trash/restore/?$', AdminTrashRestoreView.as_view(), name='admin_trash_restore'),
    re_path(r'^admin/trash/purge/?$', AdminTrashPurgeView.as_view(), name='admin_trash_purge'),

    # Load Fixtures utility endpoint
    re_path(r'^load-fixtures/?$', load_fixtures_view, name='load_fixtures'),

    # Default router URLs
    re_path(r'^', include(router.urls)),
]
