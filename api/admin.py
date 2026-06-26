import re
from django import forms
from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import (
    Artist, Album, Song, Playlist, CustomUser, Genre, 
    Subscription, DownloadLog, ListeningHistory, Banner, 
    Announcement, FAQ, SystemSetting, ActivityLog
)

class ActionsMixin:
    def row_actions(self, obj):
        app_label = obj._meta.app_label
        model_name = obj._meta.model_name
        edit_url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.pk])
        delete_url = reverse(f"admin:{app_label}_{model_name}_delete", args=[obj.pk])
        return format_html(
            '<div class="flex items-center gap-2">'
            '  <a href="{}" class="inline-flex items-center justify-center h-7 px-2.5 rounded-md border border-gray-200 dark:border-base-800 text-[10px] font-bold text-gray-600 dark:text-gray-300 bg-white dark:bg-base-950 hover:bg-primary-50 dark:hover:bg-primary-950/20 hover:text-primary-600 dark:hover:text-primary-500 transition-colors">Edit</a>'
            '  <a href="{}" class="inline-flex items-center justify-center h-7 px-2.5 rounded-md border border-red-200 dark:border-red-950/30 text-[10px] font-bold text-red-600 dark:text-red-500 bg-white dark:bg-base-950 hover:bg-red-50 dark:hover:bg-red-950/20 hover:text-red-700 dark:hover:text-red-400 transition-colors">Delete</a>'
            '</div>',
            edit_url,
            delete_url
        )
    row_actions.short_description = "Actions"

@admin.register(Genre)
class GenreAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'name', 'description', 'row_actions')
    search_fields = ('name',)

@admin.register(Artist)
class ArtistAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'name', 'deleted_at', 'row_actions')
    search_fields = ('name',)

@admin.register(Album)
class AlbumAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'name', 'artist', 'release_year', 'deleted_at', 'row_actions')
    list_filter = ('artist', 'release_year')
    search_fields = ('name', 'artist__name')

class SongForm(forms.ModelForm):
    duration_formatted = forms.CharField(
        label="Duration (MM:SS)",
        required=True,
        help_text="Enter duration in MM:SS format (e.g., 02:40 or 4:00)",
        widget=forms.TextInput(attrs={'placeholder': 'MM:SS (e.g., 02:40)'})
    )

    class Meta:
        model = Song
        fields = '__all__'
        exclude = ('duration_ms',)
        widgets = {
            'lyrics': Textarea(
                attrs={
                    'rows': 20,
                    'cols': 90,
                    'style': 'font-family: monospace; font-size: 14px;',
                    'placeholder': 'Paste LRC formatted lyrics here, e.g.,\n[00:04.00] Dabe Dabe, egi Nupe\n[00:08.50] ...'
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.duration_ms:
            total_seconds = self.instance.duration_ms // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            self.fields['duration_formatted'].initial = f"{minutes:02d}:{seconds:02d}"

    def clean_duration_formatted(self):
        data = self.cleaned_data.get('duration_formatted')
        if not data:
            raise forms.ValidationError("Duration is required.")
        
        parts = data.strip().split(':')
        if len(parts) == 2:
            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
                if seconds < 0 or seconds >= 60 or minutes < 0:
                    raise ValueError()
                return (minutes * 60 + seconds) * 1000
            except ValueError:
                raise forms.ValidationError("Invalid format. Use MM:SS (e.g., 02:40).")
        elif len(parts) == 3:
            try:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                if minutes < 0 or minutes >= 60 or seconds < 0 or seconds >= 60 or hours < 0:
                    raise ValueError()
                return (hours * 3600 + minutes * 60 + seconds) * 1000
            except ValueError:
                raise forms.ValidationError("Invalid format. Use HH:MM:SS or MM:SS.")
        else:
            try:
                seconds = int(data.strip())
                if seconds < 0:
                    raise ValueError()
                return seconds * 1000
            except ValueError:
                raise forms.ValidationError("Invalid format. Use MM:SS (e.g., 02:40).")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.duration_ms = self.cleaned_data.get('duration_formatted')
        if commit:
            instance.save()
            self.save_m2m()
        return instance

@admin.register(Song)
class SongAdmin(ActionsMixin, ModelAdmin):
    form = SongForm
    list_display = ('id', 'title', 'artist', 'album', 'duration_display', 'deleted_at', 'row_actions')
    list_filter = ('artist', 'album')
    search_fields = ('title', 'artist__name', 'album__name')
    fields = ('title', 'artist', 'album', 'genre', 'audio_file', 'artwork', 'duration_formatted', 'lyrics', 'deleted_at')

    def duration_display(self, obj):
        if obj.duration_ms:
            total_seconds = obj.duration_ms // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "-"
    duration_display.short_description = "Duration"
    duration_display.admin_order_field = 'duration_ms'

@admin.register(Playlist)
class PlaylistAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at', 'deleted_at', 'row_actions')
    list_filter = ('user',)
    search_fields = ('name', 'user__username')
    filter_horizontal = ('songs',)

@admin.register(CustomUser)
class CustomUserAdmin(ActionsMixin, BaseUserAdmin, ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'deleted_at', 'row_actions')
    filter_horizontal = BaseUserAdmin.filter_horizontal + ('favorite_songs',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Favorites', {'fields': ('favorite_songs',)}),
    )

@admin.register(Subscription)
class SubscriptionAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'user', 'plan', 'status', 'price', 'billing_cycle', 'next_billing_date', 'row_actions')
    list_filter = ('plan', 'status', 'billing_cycle')
    search_fields = ('user__username', 'user__email')

@admin.register(DownloadLog)
class DownloadLogAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'user', 'song', 'downloaded_at', 'ip_address', 'device', 'row_actions')
    list_filter = ('downloaded_at', 'device')
    search_fields = ('user__username', 'song__title', 'ip_address')

@admin.register(ListeningHistory)
class ListeningHistoryAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'user', 'song', 'played_at', 'duration_seconds', 'row_actions')
    list_filter = ('played_at',)
    search_fields = ('user__username', 'song__title')

@admin.register(Banner)
class BannerAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'title', 'order', 'is_active', 'created_at', 'row_actions')
    list_filter = ('is_active',)
    search_fields = ('title',)

@admin.register(Announcement)
class AnnouncementAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'title', 'target', 'is_active', 'created_at', 'row_actions')
    list_filter = ('target', 'is_active')
    search_fields = ('title', 'content')

@admin.register(FAQ)
class FAQAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'question', 'category', 'order', 'row_actions')
    list_filter = ('category',)
    search_fields = ('question', 'answer')

@admin.register(SystemSetting)
class SystemSettingAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'app_name', 'maintenance_mode', 'allowed_upload_size_mb', 'row_actions')

@admin.register(ActivityLog)
class ActivityLogAdmin(ActionsMixin, ModelAdmin):
    list_display = ('id', 'user', 'action', 'details', 'created_at', 'row_actions')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'action', 'details')
