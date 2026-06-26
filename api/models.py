from django.db import models
from django.contrib.auth.models import AbstractUser

class Artist(models.Model):
    name = models.CharField(max_length=255, unique=True)
    image = models.ImageField(upload_to='artists/', null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Album(models.Model):
    name = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="albums")
    artwork = models.ImageField(upload_to='albums/')
    release_year = models.IntegerField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.artist.name}"

class Genre(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Song(models.Model):
    title = models.CharField(max_length=255)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="songs")
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name="songs")
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name="songs")
    audio_file = models.FileField(upload_to='songs/')
    artwork = models.ImageField(upload_to='songs/artwork/', null=True, blank=True)
    duration_ms = models.IntegerField()
    lyrics = models.TextField(blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.artist.name}"

    @property
    def effective_artwork(self):
        """
        Returns the song's artwork if present, otherwise falls back to its album's artwork.
        """
        if self.artwork:
            return self.artwork
        elif self.album and self.album.artwork:
            return self.album.artwork
        return None

class CustomUser(AbstractUser):
    favorite_songs = models.ManyToManyField(Song, blank=True, related_name="favorited_by")
    last_active_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username

class Playlist(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="playlists")
    songs = models.ManyToManyField(Song, related_name="playlists", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class Subscription(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=50) # "Free" | "Premium"
    status = models.CharField(max_length=50) # "Active" | "Cancelled" | "Expired"
    price = models.FloatField()
    billing_cycle = models.CharField(max_length=50) # "Monthly" | "Yearly"
    next_billing_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan} ({self.status})"

class DownloadLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="downloads")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="downloads")
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} downloaded {self.song.title}"

class ListeningHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="history")
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="history")
    played_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} played {self.song.title}"

class Banner(models.Model):
    title = models.CharField(max_length=255)
    image_url = models.CharField(max_length=1024)
    link_url = models.CharField(max_length=1024, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    target = models.CharField(max_length=50, default="All") # "All" | "Premium"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class FAQ(models.Model):
    question = models.CharField(max_length=1024)
    answer = models.TextField()
    category = models.CharField(max_length=255, default="General")
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.question

class SystemSetting(models.Model):
    app_name = models.CharField(max_length=255, default="Nupe Songs")
    maintenance_mode = models.BooleanField(default=False)
    allowed_upload_size_mb = models.IntegerField(default=20)

    def __str__(self):
        return self.app_name

class ActivityLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="activities")
    action = models.CharField(max_length=255)
    details = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action}"
