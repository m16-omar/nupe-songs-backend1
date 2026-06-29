import json
import calendar
from datetime import timedelta
from django.utils import timezone
from .models import Artist, Album, Song, Playlist, CustomUser

def dashboard_callback(request, context):
    """
    Callback for django-unfold to inject data into the admin dashboard matching Lovable's Nupe Songs app.
    """
    db_users_count = CustomUser.objects.count()
    db_songs_count = Song.objects.count()
    db_artists_count = Artist.objects.count()
    db_albums_count = Album.objects.count()
    db_playlists_count = Playlist.objects.count()

    # Replicate exact default values from the Lovable app code with database variation
    users_val = 24532 + max(0, db_users_count - 1)
    songs_val = 18392 + max(0, db_songs_count - 1)
    
    # Calculate streams, downloads and revenue dynamically based on database contents
    streams_val = 2.45 + (db_songs_count * 0.01)
    downloads_val = 482345 + (db_playlists_count * 45)
    revenue_val = 48392 + (db_songs_count * 75)

    # Format values matching Lovable representations
    total_users_str = f"{users_val:,}"
    total_songs_str = f"{songs_val:,}"
    total_streams_str = f"{streams_val:.2f}M"
    downloads_str = f"{downloads_val:,}"
    revenue_str = f"${revenue_val:,}"

    context.update({
        "total_users_str": total_users_str,
        "total_songs_str": total_songs_str,
        "total_streams_str": total_streams_str,
        "downloads_str": downloads_str,
        "revenue_str": revenue_str,
    })

    # Bottom progress cards
    active_subs = 8542 + max(0, db_users_count - 1)
    free_users = 15990 + max(0, db_users_count - 1)
    storage_val = 1.24 + (db_songs_count * 0.002)

    context.update({
        "active_subs_str": f"{active_subs:,}",
        "free_users_str": f"{free_users:,}",
        "storage_used_str": f"{storage_val:.2f} TB",
    })

    # Streaming Overview Chart.js Data (Streams and Listeners over time)
    # Renders the wave line from the react code
    now = timezone.now()
    labels = []
    streams_data = []
    listeners_data = []
    
    base_streams = [500000, 580000, 620000, 590000, 680000, 650000, 720000]
    base_listeners = [250000, 290000, 310000, 280000, 340000, 320000, 370000]

    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        labels.append(f"May {12 + (6 - i)}")
        streams_data.append(base_streams[6 - i] + db_songs_count * 1500)
        listeners_data.append(base_listeners[6 - i] + db_users_count * 800)

    # User Growth Bar Chart Data (New users over time)
    user_growth_data = []
    base_users = [1800, 2400, 2900, 2500, 3200, 2800, 3500]
    for i in range(7):
        user_growth_data.append(base_users[i] + db_users_count * 20)

    context.update({
        "chart_labels": json.dumps(labels),
        "streams_data": json.dumps(streams_data),
        "listeners_data": json.dumps(listeners_data),
        "user_growth_data": json.dumps(user_growth_data),
    })

    # Top Songs (Most streamed songs) matching the Lovable list exactly
    top_songs = [
        {"title": "Blinding Lights", "artist": "The Weeknd", "plays": "2.4M", "color": "#6c50e9"},
        {"title": "Shape of You", "artist": "Ed Sheeran", "plays": "1.9M", "color": "#10B981"},
        {"title": "Someone You Loved", "artist": "Lewis Capaldi", "plays": "1.7M", "color": "#3B82F6"},
        {"title": "Sunflower", "artist": "Post Malone, Swae Lee", "plays": "1.5M", "color": "#F97316"},
        {"title": "Stay", "artist": "The Kid LAROI, Justin Bieber", "plays": "1.3M", "color": "#fc4a93"}
    ]

    # Integrate actual database songs in Top Songs if we have them
    db_songs = Song.objects.select_related('artist').order_by('-id')[:3]
    for idx, db_song in enumerate(db_songs):
        if idx < len(top_songs):
            # Calculate mock plays based on song ID
            plays_count = 1.0 + (db_song.id * 0.1)
            # Find artwork url
            art_color = ["#6c50e9", "#10B981", "#3B82F6", "#F97316", "#fc4a93"][idx % 5]
            top_songs[idx] = {
                "title": db_song.title,
                "artist": db_song.artist.name,
                "plays": f"{plays_count:.1f}M",
                "color": art_color,
                "artwork": db_song.effective_artwork.url if db_song.effective_artwork else None
            }

    context["top_songs"] = top_songs

    # Recent Songs Table matching Lovable's list
    recent_songs_list = [
        {"title": "Die For You", "artist": "The Weeknd", "album": "Starboy", "date": "May 18, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20"},
        {"title": "Calm Down", "artist": "Rema", "album": "Rave & Roses", "date": "May 18, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20"},
        {"title": "Flowers", "artist": "Miley Cyrus", "album": "Endless Summer", "date": "May 17, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20"},
        {"title": "Anti-Hero", "artist": "Taylor Swift", "album": "Midnights", "date": "May 17, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20"},
        {"title": "Creepin'", "artist": "Metro Boomin, The Weeknd", "album": "Heroes & Villains", "date": "May 16, 2024", "status": "Draft", "status_class": "bg-gray-100 text-gray-700 dark:bg-base-800 dark:text-gray-300 border border-gray-200 dark:border-base-700"},
        {"title": "As It Was", "artist": "Harry Styles", "album": "Harry's House", "date": "May 16, 2024", "status": "Published", "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20"}
    ]

    # Integrate actual database songs at the top of the list
    all_db_songs = Song.objects.select_related('artist', 'album').order_by('-id')[:4]
    for idx, song in enumerate(all_db_songs):
        if idx < len(recent_songs_list):
            try:
                artwork_url = song.effective_artwork.url if song.effective_artwork else None
            except Exception:
                artwork_url = None
            recent_songs_list[idx] = {
                "title": song.title,
                "artist": song.artist.name,
                "album": song.album.name if song.album else "Single",
                "date": song.album.release_year if (song.album and song.album.release_year) else "Recently",
                "status": "Published",
                "status_class": "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20",
                "artwork": artwork_url
            }

    context["recent_songs"] = recent_songs_list

    # Recent Users Table matching Lovable's list
    recent_users_list = [
        {"name": "Jane Cooper", "email": "jane@example.com", "date": "May 18, 2024", "initials": "JC", "color": "linear-gradient(135deg, #6c50e9, #fc4a93)"},
        {"name": "Cody Fisher", "email": "cody@example.com", "date": "May 18, 2024", "initials": "CF", "color": "linear-gradient(135deg, #3B82F6, #6c50e9)"},
        {"name": "Esther Howard", "email": "esther@example.com", "date": "May 17, 2024", "initials": "EH", "color": "linear-gradient(135deg, #10B981, #3B82F6)"},
        {"name": "Robert Fox", "email": "robert@example.com", "date": "May 17, 2024", "initials": "RF", "color": "linear-gradient(135deg, #F97316, #10B981)"},
        {"name": "Wade Warren", "email": "wade@example.com", "date": "May 16, 2024", "initials": "WW", "color": "linear-gradient(135deg, #fc4a93, #F97316)"},
        {"name": "Brooklyn Simmons", "email": "brooklyn@example.com", "date": "May 16, 2024", "initials": "BS", "color": "linear-gradient(135deg, #6c50e9, #3B82F6)"}
    ]

    # Integrate actual database users at the top
    all_db_users = CustomUser.objects.filter(is_superuser=False).order_by('-date_joined')[:3]
    for idx, user in enumerate(all_db_users):
        if idx < len(recent_users_list):
            user_name = user.get_full_name() or user.username
            initials = "".join([n[0].upper() for n in user_name.split() if n])[:2] or user.username[:2].upper()
            gradient = [
                "linear-gradient(135deg, #6c50e9, #fc4a93)",
                "linear-gradient(135deg, #3B82F6, #6c50e9)",
                "linear-gradient(135deg, #10B981, #3B82F6)"
            ][idx % 3]

            recent_users_list[idx] = {
                "name": user_name,
                "email": user.email or f"{user.username}@example.com",
                "date": user.date_joined.strftime("%b %d, %Y"),
                "initials": initials,
                "color": gradient
            }

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

