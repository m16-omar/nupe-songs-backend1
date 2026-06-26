from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Artist, Album, Song, Playlist, Genre, Subscription, 
    DownloadLog, ListeningHistory, Banner, Announcement, FAQ, 
    SystemSetting, ActivityLog
)

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class SimpleArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ('id', 'name', 'image')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if instance.image:
            if request:
                ret['image'] = request.build_absolute_uri(instance.image.url)
            else:
                ret['image'] = instance.image.url
        else:
            ret['image'] = None
        return ret

class SimpleAlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ('id', 'name', 'artwork', 'release_year')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if instance.artwork:
            if request:
                ret['artwork'] = request.build_absolute_uri(instance.artwork.url)
            else:
                ret['artwork'] = instance.artwork.url
        else:
            ret['artwork'] = None
        return ret

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name', 'description')

class SongSerializer(serializers.ModelSerializer):
    artist = SimpleArtistSerializer(read_only=True)
    album = SimpleAlbumSerializer(read_only=True)
    genre = GenreSerializer(read_only=True)
    artwork_url = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    audio_file = serializers.SerializerMethodField()
    stream_url = serializers.SerializerMethodField()
    stream_count = serializers.SerializerMethodField()
    download_count = serializers.SerializerMethodField()

    class Meta:
        model = Song
        fields = ('id', 'title', 'artist', 'album', 'genre', 'audio_file', 'stream_url', 'artwork_url', 'duration_ms', 'lyrics', 'is_favorited', 'stream_count', 'download_count')

    def get_artwork_url(self, obj):
        request = self.context.get('request')
        artwork = obj.effective_artwork
        if artwork:
            if request:
                return request.build_absolute_uri(artwork.url)
            return artwork.url
        return None

    def get_audio_file(self, obj):
        request = self.context.get('request')
        if obj.audio_file:
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
            return obj.audio_file.url
        return None

    def get_stream_url(self, obj):
        return self.get_audio_file(obj)

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return request.user.favorite_songs.filter(id=obj.id).exists()
        return False

    def get_stream_count(self, obj):
        from .models import ListeningHistory
        return ListeningHistory.objects.filter(song=obj).count()

    def get_download_count(self, obj):
        from .models import DownloadLog
        return DownloadLog.objects.filter(song=obj).count()

class UserMeSerializer(serializers.ModelSerializer):
    favorite_songs = SongSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'favorite_songs')

class AlbumWithSongsSerializer(serializers.ModelSerializer):
    artist = SimpleArtistSerializer(read_only=True)
    songs = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = ('id', 'name', 'artist', 'artwork', 'release_year', 'songs')

    def get_songs(self, obj):
        # Only non-deleted songs
        songs = obj.songs.filter(deleted_at__isnull=True)
        return SongSerializer(songs, many=True, context=self.context).data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if instance.artwork:
            if request:
                ret['artwork'] = request.build_absolute_uri(instance.artwork.url)
            else:
                ret['artwork'] = instance.artwork.url
        else:
            ret['artwork'] = None
        return ret

class ArtistDetailSerializer(serializers.ModelSerializer):
    songs = serializers.SerializerMethodField()
    albums = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = ('id', 'name', 'image', 'songs', 'albums')

    def get_songs(self, obj):
        songs = obj.songs.filter(deleted_at__isnull=True)
        return SongSerializer(songs, many=True, context=self.context).data

    def get_albums(self, obj):
        albums = obj.albums.filter(deleted_at__isnull=True)
        return SimpleAlbumSerializer(albums, many=True, context=self.context).data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if instance.image:
            if request:
                ret['image'] = request.build_absolute_uri(instance.image.url)
            else:
                ret['image'] = instance.image.url
        else:
            ret['image'] = None
        return ret

class PlaylistSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    songs = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ('id', 'name', 'user', 'songs', 'created_at')

    def get_songs(self, obj):
        songs = obj.songs.filter(deleted_at__isnull=True)
        return SongSerializer(songs, many=True, context=self.context).data

class SubscriptionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'plan', 'status', 'price', 'billing_cycle', 'next_billing_date', 'created_at', 'user')

    def get_user(self, obj):
        return {
            'username': obj.user.username,
            'email': obj.user.email
        }

class DownloadLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    song_title = serializers.CharField(source='song.title', read_only=True)
    artist_name = serializers.CharField(source='song.artist.name', read_only=True)

    class Meta:
        model = DownloadLog
        fields = ('id', 'downloaded_at', 'ip_address', 'device', 'username', 'song_title', 'artist_name')

class ListeningHistorySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    song_title = serializers.CharField(source='song.title', read_only=True)
    artist_name = serializers.CharField(source='song.artist.name', read_only=True)

    class Meta:
        model = ListeningHistory
        fields = ('id', 'played_at', 'duration_seconds', 'username', 'song_title', 'artist_name')

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'title', 'image_url', 'link_url', 'is_active', 'order', 'created_at')

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ('id', 'title', 'content', 'target', 'is_active', 'created_at')

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ('id', 'question', 'answer', 'category', 'order')

class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ('id', 'app_name', 'maintenance_mode', 'allowed_upload_size_mb')

class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ('id', 'action', 'details', 'created_at', 'username')
