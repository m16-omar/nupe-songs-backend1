from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from api.models import (
    Artist, Album, Song, Playlist, Genre, Subscription, 
    DownloadLog, ListeningHistory, Banner, Announcement, FAQ, 
    SystemSetting, ActivityLog
)

class Command(BaseCommand):
    help = 'Seeds the database with expanded models matching Next.js Prisma seed'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database with expanded models...')

        # 1. Clear existing records in reverse dependency order
        ActivityLog.objects.all().delete()
        SystemSetting.objects.all().delete()
        FAQ.objects.all().delete()
        Announcement.objects.all().delete()
        Banner.objects.all().delete()
        ListeningHistory.objects.all().delete()
        DownloadLog.objects.all().delete()
        Subscription.objects.all().delete()
        
        # Clear ManyToMany before deleting playlists
        for p in Playlist.objects.all():
            p.songs.clear()
        Playlist.objects.all().delete()

        # Clear ManyToMany for users
        User = get_user_model()
        for u in User.objects.all():
            u.favorite_songs.clear()
        
        Song.objects.all().delete()
        Album.objects.all().delete()
        Artist.objects.all().delete()
        Genre.objects.all().delete()
        User.objects.all().delete()

        self.stdout.write('Existing records cleared.')

        # 2. Create Users
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@nupesongs.com',
            password='admin123'
        )

        fan = User.objects.create_user(
            username='nupe_fan',
            email='fan@nupe.com',
            password='testpassword123'
        )

        fan2 = User.objects.create_user(
            username='jane_cooper',
            email='jane@example.com',
            password='testpassword123'
        )

        self.stdout.write('Users created.')

        # 3. Create Subscriptions
        Subscription.objects.create(
            plan='Premium',
            status='Active',
            price=9.99,
            billing_cycle='Monthly',
            next_billing_date=timezone.now() + timedelta(days=30),
            user=fan
        )

        Subscription.objects.create(
            plan='Free',
            status='Active',
            price=0.0,
            billing_cycle='Monthly',
            next_billing_date=timezone.now() + timedelta(days=30),
            user=fan2
        )

        self.stdout.write('Subscriptions seeded.')

        # 4. Create Genres
        genre_traditional = Genre.objects.create(
            name='Traditional', 
            description='Traditional folk music of the Nupe kingdom'
        )
        genre_gospel = Genre.objects.create(
            name='Gospel', 
            description='Inspirational christian rhythms and hymnals'
        )
        genre_afrobeats = Genre.objects.create(
            name='Afrobeats', 
            description='Modern African popular beats and synthesisers'
        )
        genre_soul = Genre.objects.create(
            name='Soul/RnB', 
            description='Slow acoustic vocals and rhythmic beats'
        )

        self.stdout.write('Genres created.')

        # 5. Create Artists
        artist1 = Artist.objects.create(name='Bassa Artist', image='artists/bassa_artist.jpg')
        artist2 = Artist.objects.create(name='The Weeknd', image='artists/the_weeknd.jpg')
        artist3 = Artist.objects.create(name='Ed Sheeran', image='artists/ed_sheeran.jpg')
        artist4 = Artist.objects.create(name='Lewis Capaldi', image='artists/lewis_capaldi.jpg')

        self.stdout.write('Artists created.')

        # 6. Create Albums
        album1 = Album.objects.create(
            name='Nupe Classics',
            release_year=2024,
            artwork='albums/nupe_classics.jpg',
            artist=artist1
        )
        album2 = Album.objects.create(
            name='Starboy',
            release_year=2016,
            artwork='albums/starboy.jpg',
            artist=artist2
        )
        album3 = Album.objects.create(
            name='Divide',
            release_year=2017,
            artwork='albums/divide.jpg',
            artist=artist3
        )

        self.stdout.write('Albums created.')

        # 7. Create Songs
        song1 = Song.objects.create(
            title='Dabe Dabe',
            audio_file='songs/dabe_dabe.mp3',
            duration_ms=240000,
            lyrics='[00:04.00] Dabe Dabe, egi Nupe\n[00:08.50] Dabe Dabe, egi Nupe\n[00:12.00] Beautiful music from the Nupe land.',
            artist=artist1,
            album=album1,
            genre=genre_traditional
        )

        song2 = Song.objects.create(
            title='Nupe Groove',
            audio_file='songs/nupe_groove.mp3',
            artwork='songs/artwork/nupe_groove.jpg',
            duration_ms=180000,
            lyrics='[00:02.00] Nupe Groove\n[00:06.00] Dance to the beat of the Nupe drum\n[00:10.00] Feel the rhythm in your heart.',
            artist=artist1,
            album=album1,
            genre=genre_traditional
        )

        song3 = Song.objects.create(
            title='Blinding Lights',
            audio_file='songs/blinding_lights.mp3',
            artwork='songs/artwork/blinding_lights.jpg',
            duration_ms=200000,
            lyrics="[00:05.00] I've been tryna call\n[00:08.00] I've been on my own for long enough",
            artist=artist2,
            album=album2,
            genre=genre_afrobeats
        )

        song4 = Song.objects.create(
            title='Shape of You',
            audio_file='songs/shape_of_you.mp3',
            duration_ms=220000,
            lyrics="[00:02.00] The club isn't the best place to find a lover\n[00:05.00] So the bar is where I go",
            artist=artist3,
            album=album3,
            genre=genre_soul
        )

        song5 = Song.objects.create(
            title='Someone You Loved',
            audio_file='songs/someone_you_loved.mp3',
            artwork='songs/artwork/someone_you_loved.jpg',
            duration_ms=190000,
            lyrics="[00:04.00] I'm going under and this time I fear there's no one to save me\n[00:09.00] This all or nothing really got a way of driving me crazy",
            artist=artist4,
            genre=genre_soul
        )

        self.stdout.write('Songs seeded.')

        # 8. Connect favorites & playlists
        fan.favorite_songs.add(song1, song2)
        
        playlist = Playlist.objects.create(
            name='My Nupe Mix',
            user=fan
        )
        playlist.songs.add(song1)

        self.stdout.write('Favorites & playlists connected.')

        # 9. Seed Logs (Downloads & listening history)
        DownloadLog.objects.create(
            ip_address='192.168.1.15',
            device='iPhone 15 Pro Max',
            user=fan,
            song=song1
        )

        DownloadLog.objects.create(
            ip_address='102.168.1.20',
            device='Samsung Galaxy S24',
            user=fan2,
            song=song2
        )

        ListeningHistory.objects.create(
            duration_seconds=154,
            user=fan,
            song=song1
        )

        ListeningHistory.objects.create(
            duration_seconds=180,
            user=fan2,
            song=song2
        )

        self.stdout.write('Logs seeded.')

        # 10. Seed Content (Banners, Announcements, FAQs)
        Banner.objects.create(
            title='Nupe Traditional Music Festival 2026',
            image_url='https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&auto=format&fit=crop&q=60',
            link_url='/events/traditional-fest-2026',
            order=1,
            is_active=True
        )

        Banner.objects.create(
            title='Top Traditional Hits Playlist Out Now!',
            image_url='https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800&auto=format&fit=crop&q=60',
            link_url='/playlists/1',
            order=2,
            is_active=True
        )

        Announcement.objects.create(
            title='Scheduled Server Maintenance',
            content='We will be conducting database tuning on June 20, 2026. Expect minor interruptions.',
            target='All',
            is_active=True
        )

        Announcement.objects.create(
            title='Exclusive High-Fidelity Audio Tier Available Now!',
            content='Unlock 320kbps high fidelity streaming on your account dashboard today.',
            target='Premium',
            is_active=True
        )

        FAQ.objects.create(
            question='How do I download songs offline?',
            answer='Go to any track details card and hit the "Download" button. Downloaded songs will appear in your local library.',
            category='Downloads',
            order=1
        )

        FAQ.objects.create(
            question='Can I cancel my subscription anytime?',
            answer='Yes, navigate to Settings > Billing and press "Cancel Subscription" to stop recurring billing immediately.',
            category='Billing',
            order=2
        )

        self.stdout.write('CMS seeded.')

        # 11. System Settings & Activity Logs
        SystemSetting.objects.create(
            id=1,
            app_name='Nupe Songs Portal',
            maintenance_mode=False,
            allowed_upload_size_mb=25
        )

        ActivityLog.objects.create(
            action='APP_INITIALIZATION',
            details='Next.js backend and local SQLite DB initialized successfully.',
            user=admin
        )

        ActivityLog.objects.create(
            action='SONG_CREATE',
            details='Admin created new song: Dabe Dabe.',
            user=admin
        )

        self.stdout.write('System settings and logs seeded.')
        self.stdout.write(self.style.SUCCESS('Expanded database seeding completed successfully! 🚀'))
