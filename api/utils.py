from django.db import models
from .models import Artist, Album, Song, Playlist, CustomUser, Subscription, DownloadLog, ListeningHistory

def format_stat_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M".replace(".00M", "M")
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K".replace(".0K", "K")
    return str(num)

def get_weekly_change(queryset, date_field):
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)
    
    current_count = queryset.filter(**{f"{date_field}__gte": seven_days_ago}).count()
    previous_count = queryset.filter(**{f"{date_field}__range": (fourteen_days_ago, seven_days_ago)}).count()
    
    if previous_count == 0:
        if current_count > 0:
            return "↑ +100.0%"
        else:
            return "+0.0%"
            
    pct_change = ((current_count - previous_count) / previous_count) * 100.0
    sign = "+" if pct_change >= 0 else ""
    arrow = "↑" if pct_change >= 0 else "↓"
    return f"{arrow} {sign}{pct_change:.1f}%"

def dashboard_callback(request, context):
    """
    Callback for django-unfold to inject data into the admin dashboard matching Lovable's Nupe Songs app.
    """
    db_users_count = CustomUser.objects.filter(deleted_at__isnull=True).count()
    db_songs_count = Song.objects.filter(deleted_at__isnull=True).count()
    db_streams_count = ListeningHistory.objects.count()
    db_downloads_count = DownloadLog.objects.count()
    
    # Calculate revenue from Active subscriptions
    revenue_val = Subscription.objects.filter(status="Active").aggregate(total=models.Sum('price'))['total'] or 0.0

    # Format values with dynamic real values
    total_users_str = f"{db_users_count:,}"
    total_songs_str = f"{db_songs_count:,}"
    total_streams_str = format_stat_number(db_streams_count)
    downloads_str = f"{db_downloads_count:,}"
    revenue_str = f"${revenue_val:,.2f}"

    # Calculate trends
    total_users_change = get_weekly_change(CustomUser.objects.filter(deleted_at__isnull=True), 'date_joined')
    total_songs_change = "+0.0%" # Song has no creation date field, so we show stable
    total_streams_change = get_weekly_change(ListeningHistory.objects.all(), 'played_at')
    downloads_change = get_weekly_change(DownloadLog.objects.all(), 'downloaded_at')
    revenue_change = get_weekly_change(Subscription.objects.filter(status='Active'), 'created_at')

    # Date range string for header
    now = timezone.now()
    start_date = now - timedelta(days=6)
    date_range_str = f"{start_date.strftime('%b %d')} – {now.strftime('%b %d, %Y')}"

    context.update({
        "total_users_str": total_users_str,
        "total_songs_str": total_songs_str,
        "total_streams_str": total_streams_str,
        "downloads_str": downloads_str,
        "revenue_str": revenue_str,
        "total_users_change": total_users_change,
        "total_songs_change": total_songs_change,
        "total_streams_change": total_streams_change,
        "downloads_change": downloads_change,
        "revenue_change": revenue_change,
        "date_range_str": date_range_str,
    })

    # Bottom progress cards
    active_subs = Subscription.objects.filter(status="Active").count()
    free_users = max(0, db_users_count - active_subs)
    
    # Progress bars %
    active_subs_pct = int((active_subs / db_users_count * 100)) if db_users_count > 0 else 0
    free_users_pct = int((free_users / db_users_count * 100)) if db_users_count > 0 else 0

    # Calculate storage size of all files
    total_bytes = 0
    for song in Song.objects.all():
        try:
            if song.audio_file:
                total_bytes += song.audio_file.size
        except Exception:
            pass
        try:
            if song.artwork:
                total_bytes += song.artwork.size
        except Exception:
            pass
    for album in Album.objects.all():
        try:
            if album.artwork:
                total_bytes += album.artwork.size
        except Exception:
            pass
    for artist in Artist.objects.all():
        try:
            if artist.image:
                total_bytes += artist.image.size
        except Exception:
            pass

    # 5 TB baseline limit
    storage_limit = 5 * 1024 * 1024 * 1024 * 1024
    storage_pct = min(100, int((total_bytes / storage_limit * 100))) if total_bytes > 0 else 0

    if total_bytes >= 1_099_511_627_776:
        storage_used_str = f"{total_bytes / 1_099_511_627_776:.2f} TB"
    elif total_bytes >= 1_073_741_824:
        storage_used_str = f"{total_bytes / 1_073_741_824:.2f} GB"
    elif total_bytes >= 1_048_576:
        storage_used_str = f"{total_bytes / 1_048_576:.2f} MB"
    else:
        storage_used_str = f"{total_bytes / 1024:.2f} KB"

    active_subs_change = get_weekly_change(Subscription.objects.filter(status='Active'), 'created_at')
    # Free users change (users joined recently who don't have active subscriptions)
    free_users_change = get_weekly_change(CustomUser.objects.filter(deleted_at__isnull=True).exclude(subscription__status='Active'), 'date_joined')

    context.update({
        "active_subs_str": f"{active_subs:,}",
        "free_users_str": f"{free_users:,}",
        "storage_used_str": storage_used_str,
        "active_subs_pct": active_subs_pct,
        "free_users_pct": free_users_pct,
        "storage_pct": storage_pct,
        "active_subs_change": active_subs_change,
        "free_users_change": free_users_change,
    })

    # Streaming Overview Chart.js Data (Streams and Listeners over time)
    labels = []
    streams_data = []
    listeners_data = []
    
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        labels.append(day.strftime('%b %d'))
        
        day_streams = ListeningHistory.objects.filter(played_at__range=(day_start, day_end)).count()
        day_listeners = ListeningHistory.objects.filter(played_at__range=(day_start, day_end)).values('user').distinct().count()
        
        streams_data.append(day_streams)
        listeners_data.append(day_listeners)

    # User Growth Bar Chart Data (New users over time)
    user_growth_data = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        day_users = CustomUser.objects.filter(date_joined__range=(day_start, day_end)).count()
        user_growth_data.append(day_users)

    context.update({
        "chart_labels": json.dumps(labels),
        "streams_data": json.dumps(streams_data),
        "listeners_data": json.dumps(listeners_data),
        "user_growth_data": json.dumps(user_growth_data),
    })

    # Top Songs (Most streamed songs)
    from django.db.models import Count
    top_db_songs = Song.objects.filter(deleted_at__isnull=True).annotate(
        plays_count=Count('history')
    ).order_by('-plays_count')[:5]

    top_songs = []
    colors = ["#6c50e9", "#10B981", "#3B82F6", "#F97316", "#fc4a93"]
    for idx, song in enumerate(top_db_songs):
        artwork_url = None
        try:
            if song.effective_artwork:
                artwork_url = song.effective_artwork.url
        except Exception:
            pass
            
        top_songs.append({
            "title": song.title,
            "artist": song.artist.name,
            "plays": format_stat_number(song.plays_count),
            "color": colors[idx % 5],
            "artwork": artwork_url
        })

    # Fallback to defaults if there are no songs with plays
    if not top_songs:
        default_songs = [
            {"title": "Mokwaci", "artist": "Bala MJ", "plays": "0", "color": "#6c50e9"},
            {"title": "Eganzuma", "artist": "Mahmud Mokwa", "plays": "0", "color": "#10B981"},
            {"title": "Dabe Dabe", "artist": "Mahmud Mokwa", "plays": "0", "color": "#3B82F6"},
        ]
        # Try to use any database song first
        any_songs = Song.objects.filter(deleted_at__isnull=True).select_related('artist')[:5]
        for idx, song in enumerate(any_songs):
            artwork_url = None
            try:
                if song.effective_artwork:
                    artwork_url = song.effective_artwork.url
            except Exception:
                pass
            top_songs.append({
                "title": song.title,
                "artist": song.artist.name,
                "plays": "0",
                "color": colors[idx % 5],
                "artwork": artwork_url
            })
        # Pad up to 5 if needed
        while len(top_songs) < 5 and len(default_songs) > 0:
            top_songs.append(default_songs.pop(0))

    context["top_songs"] = top_songs

    # Recent Songs Table
    recent_db_songs = Song.objects.filter(deleted_at__isnull=True).select_related('artist', 'album').order_by('-id')[:6]
    recent_songs_list = []
    for song in recent_db_songs:
        artwork_url = None
        try:
            if song.effective_artwork:
                artwork_url = song.effective_artwork.url
        except Exception:
            pass
        recent_songs_list.append({
            "title": song.title,
            "artist": song.artist.name,
            "album": song.album.name if song.album else "Single",
            "date": song.album.release_year if (song.album and song.album.release_year) else "Recently",
            "status": "Published",
            "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20",
            "artwork": artwork_url
        })
    context["recent_songs"] = recent_songs_list

    # Recent Users Table
    recent_db_users = CustomUser.objects.filter(is_superuser=False, deleted_at__isnull=True).order_by('-date_joined')[:6]
    recent_users_list = []
    for idx, user in enumerate(recent_db_users):
        user_name = user.get_full_name() or user.username
        initials = "".join([n[0].upper() for n in user_name.split() if n])[:2] or user.username[:2].upper()
        gradient = [
            "linear-gradient(135deg, #6c50e9, #fc4a93)",
            "linear-gradient(135deg, #3B82F6, #6c50e9)",
            "linear-gradient(135deg, #10B981, #3B82F6)",
            "linear-gradient(135deg, #F97316, #10B981)",
            "linear-gradient(135deg, #fc4a93, #F97316)",
            "linear-gradient(135deg, #6c50e9, #3B82F6)"
        ][idx % 6]
        recent_users_list.append({
            "name": user_name,
            "email": user.email or f"{user.username}@example.com",
            "date": user.date_joined.strftime("%b %d, %Y"),
            "initials": initials,
            "color": gradient
        })
    context["recent_users"] = recent_users_list

    return context

def cleanup_expired_trash():
    from django.utils import timezone
    from datetime import timedelta
    limit = timezone.now() - timedelta(days=30)
    Song.objects.filter(deleted_at__lt=limit).delete()
    Album.objects.filter(deleted_at__lt=limit).delete()
    Artist.objects.filter(deleted_at__lt=limit).delete()
    Playlist.objects.filter(deleted_at__lt=limit).delete()
    CustomUser.objects.filter(deleted_at__lt=limit).delete()

