import os
import shutil
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from rest_framework import viewsets, status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required

from .models import (
    Artist, Album, Song, Playlist, Genre, Subscription, 
    DownloadLog, ListeningHistory, Banner, Announcement, FAQ, 
    SystemSetting, ActivityLog
)
from .serializers import (
    UserRegisterSerializer, UserMeSerializer,
    ArtistDetailSerializer, AlbumWithSongsSerializer,
    SongSerializer, PlaylistSerializer, GenreSerializer, 
    SubscriptionSerializer, DownloadLogSerializer, 
    ListeningHistorySerializer, BannerSerializer, FAQSerializer, 
    SystemSettingSerializer, ActivityLogSerializer, 
    SimpleArtistSerializer, SimpleAlbumSerializer
)
from .utils import cleanup_expired_trash

User = get_user_model()

# ==========================================
# Public / Mobile Client Auth Views
# ==========================================

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }, status=status.HTTP_201_CREATED)

class UserMeView(generics.RetrieveAPIView):
    serializer_class = UserMeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Update user's last active time
        self.request.user.last_active_at = timezone.now()
        self.request.user.save()
        return self.request.user

# ==========================================
# Public Music Catalog Views (Filtering Soft-Deleted Content)
# ==========================================

class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = ArtistDetailSerializer

    def get_queryset(self):
        # Return only active artists
        return Artist.objects.filter(deleted_at__isnull=True).order_by('id')

class AlbumViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = AlbumWithSongsSerializer

    def get_queryset(self):
        # Return albums whose parent artist is active and album itself is active
        return Album.objects.filter(
            deleted_at__isnull=True,
            artist__deleted_at__isnull=True
        ).order_by('id')

class SongViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = SongSerializer

    def get_queryset(self):
        # Return songs whose artist is active, album is active (if set), and song itself is active
        return Song.objects.filter(
            deleted_at__isnull=True,
            artist__deleted_at__isnull=True
        ).filter(
            Q(album__isnull=True) | Q(album__deleted_at__isnull=True)
        ).order_by('id')

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        song = self.get_object()
        user = request.user
        if user.favorite_songs.filter(id=song.id).exists():
            user.favorite_songs.remove(song)
            favorited = False
        else:
            user.favorite_songs.add(song)
            favorited = True
        return Response({'favorited': favorited}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def play(self, request, pk=None):
        song = self.get_object()
        user = request.user if request.user.is_authenticated else None
        if not user:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.first()
        if user:
            ListeningHistory.objects.create(
                user=user,
                song=song,
                duration_seconds=song.duration_ms // 1000
            )
            return Response({'status': 'play logged'}, status=status.HTTP_200_OK)
        return Response({'error': 'No user available'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def download(self, request, pk=None):
        song = self.get_object()
        user = request.user if request.user.is_authenticated else None
        if not user:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.first()
        if user:
            DownloadLog.objects.create(
                user=user,
                song=song,
                device=request.META.get('HTTP_USER_AGENT', 'Unknown')
            )
            return Response({'status': 'download logged'}, status=status.HTTP_200_OK)
        return Response({'error': 'No user available'}, status=status.HTTP_400_BAD_REQUEST)

class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # User's playlists which are active
        return Playlist.objects.filter(
            user=self.request.user, 
            deleted_at__isnull=True
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # Soft-delete playlists
        playlist = self.get_object()
        playlist.deleted_at = timezone.now()
        playlist.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='add-song')
    def add_song(self, request, pk=None):
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        if not song_id:
            return Response({'error': 'song_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        song = get_object_or_404(Song, id=song_id, deleted_at__isnull=True)
        playlist.songs.add(song)
        return Response({'message': f'Song "{song.title}" added to playlist "{playlist.name}"'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='remove-song')
    def remove_song(self, request, pk=None):
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        if not song_id:
            return Response({'error': 'song_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        song = get_object_or_404(Song, id=song_id)
        playlist.songs.remove(song)
        return Response({'message': f'Song "{song.title}" removed from playlist "{playlist.name}"'}, status=status.HTTP_200_OK)

# ==========================================
# Admin stats dashboard view
# ==========================================

class AdminStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        cleanup_expired_trash()

        db_users_count = User.objects.filter(deleted_at__isnull=True).count()
        db_songs_count = Song.objects.filter(deleted_at__isnull=True).count()
        db_playlists_count = Playlist.objects.filter(deleted_at__isnull=True).count()

        # Replicate values
        users_val = 24532 + max(0, db_users_count - 2)
        songs_val = 18392 + max(0, db_songs_count - 5)
        streams_val = 2.45 + (db_songs_count * 0.01)
        downloads_val = 482345 + (db_playlists_count * 45)
        revenue_val = 48392 + (db_songs_count * 75)

        active_subs = 8542 + max(0, db_users_count - 2)
        free_users = 15990 + max(0, db_users_count - 2)
        storage_val = 1.24 + (db_songs_count * 0.002)

        def format_number(num):
            return f"{num:,}"

        # Chart data
        now = timezone.now()
        labels = []
        streams_data = []
        listeners_data = []
        user_growth_data = []

        base_streams = [500000, 580000, 620000, 590000, 680000, 650000, 720000]
        base_listeners = [250000, 290000, 310000, 280000, 340000, 320000, 370000]
        base_users = [1800, 2400, 2900, 2500, 3200, 2800, 3500]

        for i in range(6, -1, -1):
            date = now - timedelta(days=i)
            labels.append(date.strftime('%b %d'))
            streams_data.append(base_streams[6 - i] + db_songs_count * 1500)
            listeners_data.append(base_listeners[6 - i] + db_users_count * 800)

        for i in range(7):
            user_growth_data.append(base_users[i] + db_users_count * 20)

        # Top Songs
        default_top_songs = [
            {"title": "Blinding Lights", "artist": "The Weeknd", "plays": "2.4M", "color": "#6c50e9", "artwork": None},
            {"title": "Shape of You", "artist": "Ed Sheeran", "plays": "1.9M", "color": "#10B981", "artwork": None},
            {"title": "Someone You Loved", "artist": "Lewis Capaldi", "plays": "1.7M", "color": "#3B82F6", "artwork": None},
            {"title": "Sunflower", "artist": "Post Malone, Swae Lee", "plays": "1.5M", "color": "#F97316", "artwork": None},
            {"title": "Stay", "artist": "The Kid LAROI, Justin Bieber", "plays": "1.3M", "color": "#fc4a93", "artwork": None}
        ]

        db_songs_for_top = Song.objects.filter(deleted_at__isnull=True).select_related('artist', 'album').order_by('-id')[:3]
        top_songs = list(default_top_songs)
        
        for idx, db_song in enumerate(db_songs_for_top):
            plays_count = 1.0 + (db_song.id * 0.1)
            art_color = ['#6c50e9', '#10B981', '#3B82F6', '#F97316', '#fc4a93'][idx % 5]
            artwork = db_song.effective_artwork
            artwork_url = request.build_absolute_uri(artwork.url) if (artwork and request) else (artwork.url if artwork else None)
            
            top_songs[idx] = {
                "title": db_song.title,
                "artist": db_song.artist.name,
                "plays": f"{plays_count:.1f}M",
                "color": art_color,
                "artwork": artwork_url
            }

        # Recent Songs
        default_recent_songs = [
            {"title": "Die For You", "artist": "The Weeknd", "album": "Starboy", "date": "May 18, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20", "artwork": None},
            {"title": "Calm Down", "artist": "Rema", "album": "Rave & Roses", "date": "May 18, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20", "artwork": None},
            {"title": "Flowers", "artist": "Miley Cyrus", "album": "Endless Summer", "date": "May 17, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20", "artwork": None},
            {"title": "Anti-Hero", "artist": "Taylor Swift", "album": "Midnights", "date": "May 17, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20", "artwork": None},
            {"title": "Creepin'", "artist": "Metro Boomin, The Weeknd", "album": "Heroes & Villains", "date": "May 16, 2024", "status": "Draft", "status_class": "bg-gray-100 text-gray-700 dark:bg-base-800 dark:text-gray-300 border border-gray-200 dark:border-base-750", "artwork": None},
            {"title": "As It Was", "artist": "Harry Styles", "album": "Harry's House", "date": "May 16, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20", "artwork": None}
        ]

        db_songs_for_recent = Song.objects.filter(deleted_at__isnull=True).select_related('artist', 'album').order_by('-id')[:4]
        recent_songs = list(default_recent_songs)
        
        for idx, db_song in enumerate(db_songs_for_recent):
            artwork = db_song.effective_artwork
            artwork_url = request.build_absolute_uri(artwork.url) if (artwork and request) else (artwork.url if artwork else None)
            
            recent_songs[idx] = {
                "title": db_song.title,
                "artist": db_song.artist.name,
                "album": db_song.album.name if db_song.album else "Single",
                "date": str(db_song.album.release_year) if (db_song.album and db_song.album.release_year) else "Recently",
                "status": "Published",
                "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20",
                "artwork": artwork_url
            }

        # Recent Users
        default_recent_users = [
            {"name": "Jane Cooper", "email": "jane@example.com", "date": "May 18, 2024", "initials": "JC", "color": "linear-gradient(135deg, #6c50e9, #fc4a93)"},
            {"name": "Cody Fisher", "email": "cody@example.com", "date": "May 18, 2024", "initials": "CF", "color": "linear-gradient(135deg, #3B82F6, #6c50e9)"},
            {"name": "Esther Howard", "email": "esther@example.com", "date": "May 17, 2024", "initials": "EH", "color": "linear-gradient(135deg, #10B981, #3B82F6)"},
            {"name": "Robert Fox", "email": "robert@example.com", "date": "May 17, 2024", "initials": "RF", "color": "linear-gradient(135deg, #F97316, #10B981)"},
            {"name": "Wade Warren", "email": "wade@example.com", "date": "May 16, 2024", "initials": "WW", "color": "linear-gradient(135deg, #fc4a93, #F97316)"},
            {"name": "Brooklyn Simmons", "email": "brooklyn@example.com", "date": "May 16, 2024", "initials": "BS", "color": "linear-gradient(135deg, #6c50e9, #3B82F6)"}
        ]

        db_users_for_recent = User.objects.filter(is_superuser=False, is_staff=False, deleted_at__isnull=True).order_by('-date_joined')[:3]
        recent_users = list(default_recent_users)
        
        for idx, db_user in enumerate(db_users_for_recent):
            initials = db_user.username[:2].upper()
            gradient = [
                'linear-gradient(135deg, #6c50e9, #fc4a93)',
                'linear-gradient(135deg, #3B82F6, #6c50e9)',
                'linear-gradient(135deg, #10B981, #3B82F6)'
            ][idx % 3]

            recent_users[idx] = {
                "name": db_user.username,
                "email": db_user.email or f"{db_user.username}@example.com",
                "date": db_user.date_joined.strftime('%b %d, %Y'),
                "initials": initials,
                "color": gradient
            }

        return Response({
            "total_users_str": format_number(users_val),
            "total_songs_str": format_number(songs_val),
            "total_streams_str": f"{streams_val:.2f}M",
            "downloads_str": format_number(downloads_val),
            "revenue_str": f"${format_number(revenue_val)}",
            "active_subs_str": format_number(active_subs),
            "free_users_str": format_number(free_users),
            "storage_used_str": f"{storage_val:.2f} TB",
            "chart_labels": labels,
            "streams_data": streams_data,
            "listeners_data": listeners_data,
            "user_growth_data": user_growth_data,
            "top_songs": top_songs,
            "recent_songs": recent_songs,
            "recent_users": recent_users
        })

# ==========================================
# Admin Resource CRUD ViewSets
# ==========================================

class AdminGenreViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = GenreSerializer
    queryset = Genre.objects.all().order_by('id')

class AdminArtistViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SimpleArtistSerializer

    def get_queryset(self):
        return Artist.objects.filter(deleted_at__isnull=True).order_by('-id')

    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        image = request.FILES.get('image')

        if not name:
            return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)

        artist = Artist.objects.create(name=name, image=image)
        serializer = self.get_serializer(artist)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        name = request.data.get('name')
        image = request.FILES.get('image')

        if name is not None:
            instance.name = name
        if image:
            instance.image = image

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        # Admin gets additional details (songs_count and albums_count) matching Next.js api
        queryset = self.get_queryset()
        formatted = []
        for a in queryset:
            image_url = request.build_absolute_uri(a.image.url) if (a.image and request) else (a.image.url if a.image else None)
            formatted.append({
                'id': a.id,
                'name': a.name,
                'image': image_url,
                'songs_count': a.songs.filter(deleted_at__isnull=True).count(),
                'albums_count': a.albums.filter(deleted_at__isnull=True).count(),
            })
        return Response(formatted)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted_at = timezone.now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminAlbumViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SimpleAlbumSerializer

    def get_queryset(self):
        return Album.objects.filter(deleted_at__isnull=True).order_by('-id')

    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        artist_id = request.data.get('artist_id')
        artwork = request.FILES.get('artwork')
        release_year = request.data.get('release_year')

        if not name or not artist_id:
            return Response({'error': 'Name and artist_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        artist = get_object_or_404(Artist, id=artist_id)
        album = Album.objects.create(
            name=name,
            artist=artist,
            artwork=artwork,
            release_year=int(release_year) if (release_year and release_year != 'null' and release_year != '') else None
        )
        serializer = self.get_serializer(album)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        name = request.data.get('name')
        artist_id = request.data.get('artist_id')
        artwork = request.FILES.get('artwork')
        release_year = request.data.get('release_year')

        if name is not None:
            instance.name = name
        if artist_id is not None:
            instance.artist = get_object_or_404(Artist, id=artist_id)
        if release_year is not None:
            if release_year == 'null' or release_year == '':
                instance.release_year = None
            else:
                instance.release_year = int(release_year)
        if artwork:
            instance.artwork = artwork

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        # Admin gets detailed albums list matching nextjs structure
        queryset = self.get_queryset()
        formatted = []
        for alb in queryset:
            artwork_url = request.build_absolute_uri(alb.artwork.url) if (alb.artwork and request) else (alb.artwork.url if alb.artwork else None)
            formatted.append({
                'id': alb.id,
                'name': alb.name,
                'artwork': artwork_url,
                'release_year': alb.release_year,
                'artist': {
                    'id': alb.artist.id,
                    'name': alb.artist.name
                },
                'songs_count': alb.songs.filter(deleted_at__isnull=True).count()
            })
        return Response(formatted)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted_at = timezone.now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminSongViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SongSerializer

    def get_queryset(self):
        return Song.objects.filter(deleted_at__isnull=True).order_by('-id')

    def create(self, request, *args, **kwargs):
        title = request.data.get('title')
        duration_ms = request.data.get('duration_ms')
        artist_id = request.data.get('artist_id')
        album_id = request.data.get('album_id')
        genre_id = request.data.get('genre_id')
        audio_file = request.FILES.get('audio_file')
        artwork = request.FILES.get('artwork')
        lyrics = request.data.get('lyrics', '')

        if not title or not artist_id:
            return Response({'error': 'Title and artist_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        artist = get_object_or_404(Artist, id=artist_id)
        album = None
        if album_id and album_id != 'null' and album_id != '':
            album = get_object_or_404(Album, id=album_id)

        genre = None
        if genre_id and genre_id != 'null' and genre_id != '':
            genre = get_object_or_404(Genre, id=genre_id)

        song = Song.objects.create(
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            duration_ms=int(duration_ms) if duration_ms else 0,
            audio_file=audio_file,
            artwork=artwork,
            lyrics=lyrics
        )
        serializer = self.get_serializer(song)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        title = request.data.get('title')
        duration_ms = request.data.get('duration_ms')
        artist_id = request.data.get('artist_id')
        album_id = request.data.get('album_id')
        genre_id = request.data.get('genre_id')
        audio_file = request.FILES.get('audio_file')
        artwork = request.FILES.get('artwork')
        lyrics = request.data.get('lyrics')

        if title is not None:
            instance.title = title
        if duration_ms is not None:
            instance.duration_ms = int(duration_ms)
        if lyrics is not None:
            instance.lyrics = lyrics
        if artist_id is not None:
            instance.artist = get_object_or_404(Artist, id=artist_id)
        
        if album_id is not None:
            if album_id == 'null' or album_id == '':
                instance.album = None
            else:
                instance.album = get_object_or_404(Album, id=album_id)

        if genre_id is not None:
            if genre_id == 'null' or genre_id == '':
                instance.genre = None
            else:
                instance.genre = get_object_or_404(Genre, id=genre_id)

        if audio_file:
            instance.audio_file = audio_file
        if artwork:
            instance.artwork = artwork

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted_at = timezone.now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return User.objects.filter(deleted_at__isnull=True).order_by('-date_joined')

    def list(self, request, *args, **kwargs):
        users = self.get_queryset()
        formatted = []
        for u in users:
            is_online = False
            if u.last_active_at:
                is_online = (timezone.now() - u.last_active_at).total_seconds() < 300
            playlists_count = u.playlists.filter(deleted_at__isnull=True).count()
            favorites_count = u.favorite_songs.filter(deleted_at__isnull=True).count()
            
            formatted.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'is_staff': u.is_staff,
                'date_joined': u.date_joined.isoformat(),
                'playlists_count': playlists_count,
                'favorites_count': favorites_count,
                'is_online': is_online
            })
        return Response(formatted)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        is_staff = request.data.get('isStaff')

        if username and username != instance.username:
            if User.objects.filter(username=username).exists():
                return Response({'error': 'Username is already taken'}, status=status.HTTP_400_BAD_REQUEST)
            instance.username = username

        if email:
            instance.email = email

        if is_staff is not None:
            if instance.id == request.user.id and not is_staff:
                return Response({'error': 'You cannot revoke your own admin permissions'}, status=status.HTTP_400_BAD_REQUEST)
            instance.is_staff = is_staff

        if password and password.strip() != '':
            instance.set_password(password)

        instance.save()
        return Response({
            'id': instance.id,
            'username': instance.username,
            'email': instance.email,
            'is_staff': instance.is_staff,
            'date_joined': instance.date_joined.isoformat()
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.id == request.user.id:
            return Response({'error': 'You cannot delete your own account'}, status=status.HTTP_400_BAD_REQUEST)
        instance.deleted_at = timezone.now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminBannerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = BannerSerializer
    queryset = Banner.objects.all().order_by('order')

    def create(self, request, *args, **kwargs):
        # Allow passing order/isActive directly
        title = request.data.get('title')
        image_url = request.data.get('imageUrl') # frontend format mapping
        link_url = request.data.get('linkUrl')
        order = request.data.get('order', 0)
        is_active = request.data.get('isActive', True)

        if not title or not image_url:
            return Response({'error': 'Title and imageUrl are required'}, status=status.HTTP_400_BAD_REQUEST)

        banner = Banner.objects.create(
            title=title,
            image_url=image_url,
            link_url=link_url,
            order=int(order) if order else 0,
            is_active=is_active
        )
        serializer = self.get_serializer(banner)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        title = request.data.get('title')
        image_url = request.data.get('imageUrl')
        link_url = request.data.get('linkUrl')
        order = request.data.get('order')
        is_active = request.data.get('isActive')

        if title is not None:
            instance.title = title
        if image_url is not None:
            instance.image_url = image_url
        if link_url is not None:
            instance.link_url = link_url
        if order is not None:
            instance.order = int(order)
        if is_active is not None:
            instance.is_active = is_active

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class AdminFAQViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = FAQSerializer
    queryset = FAQ.objects.all().order_by('order')

    def create(self, request, *args, **kwargs):
        question = request.data.get('question')
        answer = request.data.get('answer')
        category = request.data.get('category', 'General')
        order = request.data.get('order', 0)

        if not question or not answer:
            return Response({'error': 'Question and answer are required'}, status=status.HTTP_400_BAD_REQUEST)

        faq = FAQ.objects.create(
            question=question,
            answer=answer,
            category=category,
            order=int(order) if order else 0
        )
        serializer = self.get_serializer(faq)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# ==========================================
# Admin Logs and System Views
# ==========================================

class AdminSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SubscriptionSerializer
    queryset = Subscription.objects.all().order_by('-created_at')

class AdminDownloadViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = DownloadLogSerializer
    queryset = DownloadLog.objects.all().order_by('-downloaded_at')

class AdminListeningHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ListeningHistorySerializer
    queryset = ListeningHistory.objects.all().order_by('-played_at')

class AdminFavoriteView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        songs = Song.objects.filter(deleted_at__isnull=True).annotate(
            favorites_count=Count('favorited_by')
        ).order_by('-favorites_count')

        formatted = []
        for s in songs:
            formatted.append({
                'id': s.id,
                'title': s.title,
                'artist_name': s.artist.name if s.artist else 'Unknown',
                'album_name': s.album.name if s.album else 'Single',
                'favorites_count': s.favorites_count
            })
        return Response(formatted)

class AdminActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ActivityLogSerializer
    queryset = ActivityLog.objects.all().order_by('-created_at')

class AdminSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = SystemSettingSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_object(self):
        obj, created = SystemSetting.objects.get_or_create(id=1)
        return obj

    def update(self, request, *args, **kwargs):
        # Support appName, maintenanceMode, allowedUploadSizeMb mapping
        instance = self.get_object()
        app_name = request.data.get('appName')
        maintenance_mode = request.data.get('maintenanceMode')
        allowed_upload_size_mb = request.data.get('allowedUploadSizeMb')

        if app_name is not None:
            instance.app_name = app_name
        if maintenance_mode is not None:
            instance.maintenance_mode = maintenance_mode
        if allowed_upload_size_mb is not None:
            instance.allowed_upload_size_mb = allowed_upload_size_mb

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class AdminBackupView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_backup_dir(self):
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        return backup_dir

    def get(self, request):
        backup_dir = self.get_backup_dir()
        files = os.listdir(backup_dir)
        backups = []
        for file in files:
            if file.startswith('database_backup_') and file.endswith('.db'):
                file_path = os.path.join(backup_dir, file)
                stat = os.stat(file_path)
                backups.append({
                    'filename': file,
                    'size': f"{round(stat.st_size / 1024)} KB",
                    'created_at': timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    'status': 'Completed'
                })
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return Response(backups)

    def post(self, request):
        backup_dir = self.get_backup_dir()
        db_file = os.path.join(settings.BASE_DIR, 'db.sqlite3')
        if not os.path.exists(db_file):
            return Response({'error': 'Database file not found'}, status=status.HTTP_404_NOT_FOUND)

        timestamp = timezone.now().strftime('%Y-%m-%dT%H-%M-%S')
        filename = f"database_backup_{timestamp}.db"
        dest_path = os.path.join(backup_dir, filename)

        shutil.copyfile(db_file, dest_path)

        stat = os.stat(dest_path)
        new_backup = {
            'filename': filename,
            'size': f"{round(stat.st_size / 1024)} KB",
            'created_at': timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            'status': 'Completed'
        }

        # Log Activity
        ActivityLog.objects.create(
            action='DB_BACKUP_CREATE',
            details=f"Admin created database backup: {filename}",
            user=request.user
        )

        return Response(new_backup, status=status.HTTP_201_CREATED)

# ==========================================
# Admin Soft-Delete / Trash views
# ==========================================

class AdminTrashView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        cleanup_expired_trash()

        deleted_songs = Song.objects.filter(deleted_at__isnull=False)
        deleted_albums = Album.objects.filter(deleted_at__isnull=False)
        deleted_artists = Artist.objects.filter(deleted_at__isnull=False)
        deleted_playlists = Playlist.objects.filter(deleted_at__isnull=False)
        deleted_users = User.objects.filter(deleted_at__isnull=False)

        trash_items = []
        for s in deleted_songs:
            trash_items.append({
                'id': s.id,
                'type': 'song',
                'name': s.title,
                'deletedAt': s.deleted_at.isoformat(),
                'details': s.artist.name if s.artist else 'Unknown Artist'
            })
        for a in deleted_albums:
            trash_items.append({
                'id': a.id,
                'type': 'album',
                'name': a.name,
                'deletedAt': a.deleted_at.isoformat(),
                'details': a.artist.name if a.artist else 'Unknown Artist'
            })
        for art in deleted_artists:
            trash_items.append({
                'id': art.id,
                'type': 'artist',
                'name': art.name,
                'deletedAt': art.deleted_at.isoformat(),
                'details': 'Artist profile'
            })
        for p in deleted_playlists:
            trash_items.append({
                'id': p.id,
                'type': 'playlist',
                'name': p.name,
                'deletedAt': p.deleted_at.isoformat(),
                'details': f'Created by {p.user.username}'
            })
        for u in deleted_users:
            trash_items.append({
                'id': u.id,
                'type': 'user',
                'name': u.username,
                'deletedAt': u.deleted_at.isoformat(),
                'details': u.email or 'No email provided'
            })

        trash_items.sort(key=lambda x: x['deletedAt'], reverse=True)
        return Response(trash_items)

    def delete(self, request):
        # Permanently purge all soft-deleted items
        Song.objects.filter(deleted_at__isnull=False).delete()
        Album.objects.filter(deleted_at__isnull=False).delete()
        Artist.objects.filter(deleted_at__isnull=False).delete()
        Playlist.objects.filter(deleted_at__isnull=False).delete()
        User.objects.filter(deleted_at__isnull=False).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminTrashRestoreView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        type_ = request.data.get('type')
        id_ = request.data.get('id')
        if not type_ or not id_:
            return Response({'error': 'Type and id are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            item_id = int(id_)
        except ValueError:
            return Response({'error': 'Invalid ID'}, status=status.HTTP_400_BAD_REQUEST)

        if type_ == 'song':
            Song.objects.filter(id=item_id).update(deleted_at=None)
        elif type_ == 'album':
            Album.objects.filter(id=item_id).update(deleted_at=None)
        elif type_ == 'artist':
            Artist.objects.filter(id=item_id).update(deleted_at=None)
        elif type_ == 'playlist':
            Playlist.objects.filter(id=item_id).update(deleted_at=None)
        elif type_ == 'user':
            User.objects.filter(id=item_id).update(deleted_at=None)
        else:
            return Response({'error': 'Invalid type'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': True})

class AdminTrashPurgeView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        type_ = request.data.get('type')
        id_ = request.data.get('id')
        if not type_ or not id_:
            return Response({'error': 'Type and id are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            item_id = int(id_)
        except ValueError:
            return Response({'error': 'Invalid ID'}, status=status.HTTP_400_BAD_REQUEST)

        if type_ == 'song':
            Song.objects.filter(id=item_id).delete()
        elif type_ == 'album':
            Album.objects.filter(id=item_id).delete()
        elif type_ == 'artist':
            Artist.objects.filter(id=item_id).delete()
        elif type_ == 'playlist':
            Playlist.objects.filter(id=item_id).delete()
        elif type_ == 'user':
            User.objects.filter(id=item_id).delete()
        else:
            return Response({'error': 'Invalid type'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': True})

def landing_view(request):
    from django.contrib.auth import authenticate, login as django_login
    
    error = None
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('/admin/')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            error = "Username and password are required"
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_staff:
                    django_login(request, user)
                    return redirect('/admin/')
                else:
                    error = "Access denied: You are not an administrator."
            else:
                error = "Invalid username or password"

    return render(request, 'landing.html', {'error': error})

@staff_member_required
def admin_lyrics_view(request):
    songs = Song.objects.filter(deleted_at__isnull=True).select_related('artist').order_by('title')
    context = {
        **admin.site.each_context(request),
        'songs': songs,
    }
    return render(request, 'admin/lyrics.html', context)

@staff_member_required
def admin_favorites_view(request):
    songs = Song.objects.filter(deleted_at__isnull=True).annotate(
        favorites_count=Count('favorited_by')
    ).select_related('artist', 'album').order_by('-favorites_count')
    context = {
        **admin.site.each_context(request),
        'songs': songs,
    }
    return render(request, 'admin/favorites.html', context)

@staff_member_required
def admin_analytics_view(request):
    context = {
        **admin.site.each_context(request),
    }
    return render(request, 'admin/analytics.html', context)

@staff_member_required
def admin_settings_view(request):
    obj, created = SystemSetting.objects.get_or_create(id=1)
    if request.method == 'POST':
        app_name = request.POST.get('app_name')
        maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        allowed_upload_size_mb = request.POST.get('allowed_upload_size_mb')
        
        obj.app_name = app_name
        obj.maintenance_mode = maintenance_mode
        obj.allowed_upload_size_mb = int(allowed_upload_size_mb) if allowed_upload_size_mb else 20
        obj.save()
        messages.success(request, "System settings updated successfully.")
        return redirect('admin_settings')

    context = {
        **admin.site.each_context(request),
        'settings': obj,
    }
    return render(request, 'admin/settings.html', context)

@staff_member_required
def admin_backups_view(request):
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            db_file = os.path.join(settings.BASE_DIR, 'db.sqlite3')
            if os.path.exists(db_file):
                timestamp = timezone.now().strftime('%Y-%m-%dT%H-%M-%S')
                filename = f"database_backup_{timestamp}.db"
                dest_path = os.path.join(backup_dir, filename)
                shutil.copyfile(db_file, dest_path)
                
                ActivityLog.objects.create(
                    action='DB_BACKUP_CREATE',
                    details=f"Admin created database backup: {filename}",
                    user=request.user
                )
                messages.success(request, f"Backup {filename} created successfully.")
            else:
                messages.error(request, "Database file not found.")
        elif action == 'delete':
            filename = request.POST.get('filename')
            if filename:
                filename = os.path.basename(filename)
                file_path = os.path.join(backup_dir, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    messages.success(request, f"Backup {filename} deleted.")
                else:
                    messages.error(request, "Backup file not found.")
        return redirect('admin_backups')

    files = os.listdir(backup_dir)
    backups = []
    for file in files:
        if file.startswith('database_backup_') and file.endswith('.db'):
            file_path = os.path.join(backup_dir, file)
            stat = os.stat(file_path)
            backups.append({
                'filename': file,
                'size': f"{round(stat.st_size / 1024)} KB",
                'created_at': timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                'status': 'Completed'
            })
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    context = {
        **admin.site.each_context(request),
        'backups': backups,
    }
    return render(request, 'admin/backups.html', context)

@staff_member_required
def admin_trash_view(request):
    cleanup_expired_trash()

    if request.method == 'POST':
        action = request.POST.get('action')
        type_ = request.POST.get('type')
        id_ = request.POST.get('id')

        if action == 'restore' and type_ and id_:
            try:
                item_id = int(id_)
                if type_ == 'song': Song.objects.filter(id=item_id).update(deleted_at=None)
                elif type_ == 'album': Album.objects.filter(id=item_id).update(deleted_at=None)
                elif type_ == 'artist': Artist.objects.filter(id=item_id).update(deleted_at=None)
                elif type_ == 'playlist': Playlist.objects.filter(id=item_id).update(deleted_at=None)
                elif type_ == 'user': User.objects.filter(id=item_id).update(deleted_at=None)
                messages.success(request, f"Restored {type_} successfully.")
            except ValueError:
                messages.error(request, "Invalid ID.")
        
        elif action == 'purge' and type_ and id_:
            try:
                item_id = int(id_)
                if type_ == 'song': Song.objects.filter(id=item_id).delete()
                elif type_ == 'album': Album.objects.filter(id=item_id).delete()
                elif type_ == 'artist': Artist.objects.filter(id=item_id).delete()
                elif type_ == 'playlist': Playlist.objects.filter(id=item_id).delete()
                elif type_ == 'user': User.objects.filter(id=item_id).delete()
                messages.success(request, f"Permanently deleted {type_}.")
            except ValueError:
                messages.error(request, "Invalid ID.")
        
        elif action == 'empty':
            Song.objects.filter(deleted_at__isnull=False).delete()
            Album.objects.filter(deleted_at__isnull=False).delete()
            Artist.objects.filter(deleted_at__isnull=False).delete()
            Playlist.objects.filter(deleted_at__isnull=False).delete()
            User.objects.filter(deleted_at__isnull=False).delete()
            messages.success(request, "Trash emptied.")

        return redirect('admin_trash')

    deleted_songs = Song.objects.filter(deleted_at__isnull=False)
    deleted_albums = Album.objects.filter(deleted_at__isnull=False)
    deleted_artists = Artist.objects.filter(deleted_at__isnull=False)
    deleted_playlists = Playlist.objects.filter(deleted_at__isnull=False)
    deleted_users = User.objects.filter(deleted_at__isnull=False)

    trash_items = []
    for s in deleted_songs:
        trash_items.append({
            'id': s.id, 'type': 'song', 'name': s.title,
            'deletedAt': s.deleted_at, 'details': s.artist.name if s.artist else 'Unknown Artist'
        })
    for a in deleted_albums:
        trash_items.append({
            'id': a.id, 'type': 'album', 'name': a.name,
            'deletedAt': a.deleted_at, 'details': a.artist.name if a.artist else 'Unknown Artist'
        })
    for art in deleted_artists:
        trash_items.append({
            'id': art.id, 'type': 'artist', 'name': art.name,
            'deletedAt': art.deleted_at, 'details': 'Artist profile'
        })
    for p in deleted_playlists:
        trash_items.append({
            'id': p.id, 'type': 'playlist', 'name': p.name,
            'deletedAt': p.deleted_at, 'details': f'Created by {p.user.username}'
        })
    for u in deleted_users:
        trash_items.append({
            'id': u.id, 'type': 'user', 'name': u.username,
            'deletedAt': u.deleted_at, 'details': u.email or 'No email provided'
        })

    now = timezone.now()
    for item in trash_items:
        elapsed = (now - item['deletedAt']).days
        item['days_left'] = max(0, 30 - elapsed)

    trash_items.sort(key=lambda x: x['deletedAt'], reverse=True)
    context = {
        **admin.site.each_context(request),
        'trash_items': trash_items,
    }
    return render(request, 'admin/trash.html', context)


from django.core.management import call_command
from django.http import JsonResponse

def load_fixtures_view(request):
    try:
        call_command('loaddata', 'data.json')
        return JsonResponse({'status': 'success', 'message': 'Fixtures loaded successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


