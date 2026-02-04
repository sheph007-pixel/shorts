"""
YouTube Uploader Module
Handles OAuth authentication and video upload to YouTube.
"""

import os
import json
import pickle
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# YouTube API scopes
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

# Token storage path
TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token.pickle')


class YouTubeUploader:
    """Handles YouTube authentication and video uploads."""

    def __init__(self, client_secrets_path: str = None):
        """
        Initialize the uploader.

        Args:
            client_secrets_path: Path to the OAuth client secrets JSON file
        """
        self.client_secrets_path = client_secrets_path or os.path.join(
            os.path.dirname(__file__), 'client_secrets.json'
        )
        self.credentials = None
        self.youtube = None

    def get_auth_url(self, redirect_uri: str = 'http://localhost:5000/oauth/callback') -> str:
        """
        Get the OAuth authorization URL.

        Args:
            redirect_uri: The callback URL after authorization

        Returns:
            Authorization URL to redirect the user to
        """
        if not os.path.exists(self.client_secrets_path):
            raise FileNotFoundError(
                "YouTube API client secrets not found. "
                "Please download from Google Cloud Console and save as 'client_secrets.json'"
            )

        flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        return auth_url

    def handle_oauth_callback(self, authorization_response: str, redirect_uri: str = 'http://localhost:5000/oauth/callback') -> bool:
        """
        Handle the OAuth callback and save credentials.

        Args:
            authorization_response: The full callback URL with auth code
            redirect_uri: The callback URL (must match the one used in get_auth_url)

        Returns:
            True if successful
        """
        flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        flow.fetch_token(authorization_response=authorization_response)
        self.credentials = flow.credentials

        # Save credentials for future use
        with open(TOKEN_PATH, 'wb') as token_file:
            pickle.dump(self.credentials, token_file)

        return True

    def is_authenticated(self) -> bool:
        """
        Check if we have valid credentials.

        Returns:
            True if authenticated
        """
        return self._load_credentials() is not None

    def _load_credentials(self):
        """Load and refresh credentials if needed."""
        if self.credentials and self.credentials.valid:
            return self.credentials

        # Try to load from saved token
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, 'rb') as token_file:
                self.credentials = pickle.load(token_file)

        # Refresh if expired
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                self.credentials.refresh(Request())
                # Save refreshed credentials
                with open(TOKEN_PATH, 'wb') as token_file:
                    pickle.dump(self.credentials, token_file)
            except Exception:
                self.credentials = None

        return self.credentials if (self.credentials and self.credentials.valid) else None

    def _get_youtube_service(self):
        """Get the YouTube API service."""
        credentials = self._load_credentials()
        if not credentials:
            raise Exception("Not authenticated. Please connect your YouTube account first.")

        if not self.youtube:
            self.youtube = build('youtube', 'v3', credentials=credentials)

        return self.youtube

    def get_channel_info(self) -> dict:
        """
        Get the authenticated user's channel info.

        Returns:
            Dict with channel information
        """
        youtube = self._get_youtube_service()

        response = youtube.channels().list(
            part='snippet,statistics',
            mine=True
        ).execute()

        if not response.get('items'):
            raise Exception("No YouTube channel found for this account")

        channel = response['items'][0]
        return {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'thumbnail': channel['snippet']['thumbnails']['default']['url'],
            'subscriber_count': channel['statistics'].get('subscriberCount', '0')
        }

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = '',
        tags: list = None,
        privacy_status: str = 'private',
        made_for_kids: bool = False,
        notify_subscribers: bool = True
    ) -> dict:
        """
        Upload a video to YouTube.

        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags
            privacy_status: 'private', 'unlisted', or 'public'
            made_for_kids: Whether the video is made for kids
            notify_subscribers: Whether to notify subscribers (only for public)

        Returns:
            Dict with upload result including video ID and URL
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        youtube = self._get_youtube_service()

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': '10'  # Music category
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': made_for_kids,
            }
        }

        # Only add notify subscribers if public
        if privacy_status == 'public':
            body['status']['notifySubscribers'] = notify_subscribers

        # Create media upload
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024 * 1024  # 1MB chunks
        )

        # Execute upload
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"Upload progress: {progress}%")

        video_id = response['id']

        return {
            'video_id': video_id,
            'url': f'https://youtube.com/shorts/{video_id}',
            'title': title,
            'privacy_status': privacy_status
        }

    def disconnect(self) -> bool:
        """
        Disconnect YouTube account by removing saved credentials.

        Returns:
            True if successful
        """
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
        self.credentials = None
        self.youtube = None
        return True
