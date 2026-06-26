from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Artist, Album, Song, Playlist

User = get_user_model()

class NupeSongsAPITests(APITestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='nupe_fan',
            email='fan@nupe.com',
            password='testpassword123'
        )
        # Create Artist
        self.artist = Artist.objects.create(name='Bassa Artist')
        
        # Mock file upload for artwork
        self.dummy_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
            content_type='image/jpeg'
        )
        self.dummy_audio = SimpleUploadedFile(
            name='test_song.mp3',
            content=b'fake mp3 content',
            content_type='audio/mpeg'
        )
        
        # Create Album
        self.album = Album.objects.create(
            name='Nupe Classics',
            artist=self.artist,
            artwork=self.dummy_image,
            release_year=2024
        )
        
        # Create Song with Album artwork fallback
        self.song_fallback = Song.objects.create(
            title='Dabe Dabe',
            artist=self.artist,
            album=self.album,
            audio_file=self.dummy_audio,
            duration_ms=240000,
            lyrics='[00:04.00] Dabe Dabe, egi Nupe'
        )
        
        # Create Song with its own artwork
        self.song_specific = Song.objects.create(
            title='Nupe Groove',
            artist=self.artist,
            album=self.album,
            audio_file=self.dummy_audio,
            artwork=self.dummy_image,
            duration_ms=180000,
            lyrics='[00:02.00] Nupe Groove'
        )

        # Get JWT tokens
        login_url = reverse('token_obtain_pair')
        response = self.client.post(login_url, {
            'username': 'nupe_fan',
            'password': 'testpassword123'
        })
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_user_registration(self):
        # Clear credentials for registration test
        self.client.credentials()
        register_url = reverse('auth_register')
        data = {
            'username': 'new_user',
            'email': 'new@nupe.com',
            'password': 'securepassword123'
        }
        response = self.client.post(register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'new_user')

    def test_user_login_jwt(self):
        self.client.credentials()
        login_url = reverse('token_obtain_pair')
        data = {
            'username': 'nupe_fan',
            'password': 'testpassword123'
        }
        response = self.client.post(login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_user_profile_me(self):
        profile_url = reverse('auth_me')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'nupe_fan')

    def test_music_browsing_endpoints(self):
        # Get songs list
        songs_url = reverse('song-list')
        response = self.client.get(songs_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Verify fallback artwork URL behavior
        song_fallback_data = next(s for s in response.data if s['id'] == self.song_fallback.id)
        self.assertIsNotNone(song_fallback_data['artwork_url'])
        self.assertIn(self.album.artwork.name, song_fallback_data['artwork_url'])
        
        song_specific_data = next(s for s in response.data if s['id'] == self.song_specific.id)
        self.assertIsNotNone(song_specific_data['artwork_url'])
        self.assertIn(self.song_specific.artwork.name, song_specific_data['artwork_url'])

        # Get albums list
        albums_url = reverse('album-list')
        response = self.client.get(albums_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(len(response.data[0]['songs']), 2)

        # Get artists list
        artists_url = reverse('artist-list')
        response = self.client.get(artists_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_favorite_toggling(self):
        favorite_url = reverse('song-favorite', args=[self.song_fallback.id])
        
        # Toggle: Add to favorites
        response = self.client.post(favorite_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['favorited'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.favorite_songs.filter(id=self.song_fallback.id).exists())

        # Toggle: Remove from favorites
        response = self.client.post(favorite_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['favorited'])
        self.user.refresh_from_db()
        self.assertFalse(self.user.favorite_songs.filter(id=self.song_fallback.id).exists())

    def test_playlist_actions(self):
        playlist_list_url = reverse('playlist-list')
        
        # Create a playlist
        playlist_data = {'name': 'My Nupe Mix'}
        response = self.client.post(playlist_list_url, playlist_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        playlist_id = response.data['id']
        
        # Add a song to playlist
        add_song_url = reverse('playlist-add-song', args=[playlist_id])
        response = self.client.post(add_song_url, {'song_id': self.song_fallback.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify song is in playlist
        playlist_detail_url = reverse('playlist-detail', args=[playlist_id])
        response = self.client.get(playlist_detail_url)
        self.assertEqual(len(response.data['songs']), 1)
        self.assertEqual(response.data['songs'][0]['id'], self.song_fallback.id)

        # Remove song from playlist
        remove_song_url = reverse('playlist-remove-song', args=[playlist_id])
        response = self.client.post(remove_song_url, {'song_id': self.song_fallback.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify song is removed
        response = self.client.get(playlist_detail_url)
        self.assertEqual(len(response.data['songs']), 0)

    def test_dashboard_view_permission(self):
        dashboard_url = reverse('admin:index')
        
        # Test anonymous user (should redirect to login)
        self.client.credentials()
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        
        # Test regular user (should redirect to login since not staff)
        self.client.force_login(self.user)
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        
        # Test staff user (should allow access 200 OK)
        self.user.is_staff = True
        self.user.save()
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


