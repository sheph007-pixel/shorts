"""
Simple Video Generator for YouTube Shorts
Creates vertical shorts from video clips with text overlay on black background.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, TextClip
import numpy as np


# YouTube Shorts dimensions (9:16 aspect ratio)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# Visual settings
BACKGROUND_COLOR = (0, 0, 0)  # Pure black
TEXT_COLOR = 'white'


def get_bold_font(size: int):
    """
    Get a bold font. Falls back to system fonts if not available.
    """
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            return font_path

    return None  # Will use default


def create_vertical_short(
    video_path: str,
    title: str,
    start_time: float,
    duration: float,
    output_path: str
) -> str:
    """
    Create a vertical YouTube Short from a video clip.

    Args:
        video_path: Path to the source video file
        title: Text to display on the video (bold white text)
        start_time: Start time of the clip in seconds
        duration: Duration of the clip (20-40 seconds recommended)
        output_path: Where to save the output video

    Returns:
        Path to the generated video
    """
    print(f"Loading video from {video_path}...")

    # Load video and extract clip
    video = VideoFileClip(video_path)

    # Ensure we don't exceed video duration
    if start_time + duration > video.duration:
        duration = video.duration - start_time

    # Extract the clip
    clip = video.subclip(start_time, start_time + duration)

    print(f"Creating {duration:.1f}s vertical short...")

    # Calculate scaling to fit in vertical format (9:16)
    # We'll scale the video to fit the height and center it
    original_width, original_height = clip.size

    # Calculate scale to fit height
    scale = VIDEO_HEIGHT / original_height
    new_width = int(original_width * scale)
    new_height = VIDEO_HEIGHT

    # Resize the clip
    clip_resized = clip.resize(height=new_height)

    # If video is too wide, crop it to center
    if new_width > VIDEO_WIDTH:
        x_center = new_width / 2
        x1 = int(x_center - VIDEO_WIDTH / 2)
        x2 = int(x_center + VIDEO_WIDTH / 2)
        clip_resized = clip_resized.crop(x1=x1, x2=x2)

    # Create black background
    bg = ImageClip(
        np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8),
        duration=duration
    )

    # If video is narrower than target width, center it on black background
    if new_width < VIDEO_WIDTH:
        x_pos = (VIDEO_WIDTH - new_width) / 2
        clip_resized = clip_resized.set_position((x_pos, 0))
        final_video = CompositeVideoClip([bg, clip_resized], size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    else:
        final_video = clip_resized

    # Add text overlay
    font_path = get_bold_font(80)

    try:
        text_clip = TextClip(
            title,
            fontsize=80,
            color=TEXT_COLOR,
            font=font_path if font_path else 'Arial-Bold',
            size=(VIDEO_WIDTH - 100, None),  # Max width with padding
            method='caption',
            align='center'
        ).set_duration(duration).set_position(('center', 100))

        # Composite text on video
        final_video = CompositeVideoClip([final_video, text_clip])
    except Exception as e:
        print(f"Warning: Could not add text overlay: {e}")
        print("Continuing without text...")

    # Set fps
    final_video = final_video.set_fps(FPS)

    # Write output
    print("Encoding video...")
    final_video.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        threads=4,
        logger=None  # Suppress moviepy output
    )

    # Clean up
    final_video.close()
    clip.close()
    video.close()

    print(f"Video saved to: {output_path}")
    return output_path


def auto_select_clip(video_duration: float, target_duration: float = 30) -> tuple:
    """
    Automatically select a clip from the video.
    For simplicity, takes from the beginning or a good middle section.

    Args:
        video_duration: Total duration of the video in seconds
        target_duration: Desired duration of the clip (default 30 seconds)

    Returns:
        Tuple of (start_time, duration)
    """
    # Ensure target duration doesn't exceed video duration
    clip_duration = min(target_duration, video_duration)

    # If video is short, use the whole thing
    if video_duration <= target_duration:
        return (0, video_duration)

    # Otherwise, take from the middle section (skip intro/outro)
    # Start at 20% into the video
    start_time = video_duration * 0.2

    # Ensure we have enough room
    if start_time + clip_duration > video_duration:
        start_time = video_duration - clip_duration

    return (start_time, clip_duration)
