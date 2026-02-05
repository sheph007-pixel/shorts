"""
YouTube Video Downloader Module
Downloads YouTube videos for creating shorts.
"""

import os
import yt_dlp


def download_youtube_video(url: str, output_dir: str) -> dict:
    """
    Download a YouTube video.

    Args:
        url: YouTube video URL
        output_dir: Directory to save the downloaded video

    Returns:
        dict with 'file_path', 'title', 'duration' keys
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # Prefer mp4
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract info without downloading first
        info = ydl.extract_info(url, download=False)

        # Download the video
        ydl.download([url])

        # Build file path
        video_id = info['id']
        ext = info.get('ext', 'mp4')
        file_path = os.path.join(output_dir, f"{video_id}.{ext}")

        return {
            'file_path': file_path,
            'title': info.get('title', 'Untitled'),
            'duration': info.get('duration', 0),
            'video_id': video_id
        }


def get_video_info(url: str) -> dict:
    """
    Get YouTube video information without downloading.

    Args:
        url: YouTube video URL

    Returns:
        dict with video information
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        return {
            'title': info.get('title', 'Untitled'),
            'duration': info.get('duration', 0),
            'video_id': info['id'],
            'thumbnail': info.get('thumbnail', ''),
            'description': info.get('description', ''),
        }
