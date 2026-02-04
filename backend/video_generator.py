"""
Video Generator Module
Creates a YouTube Short video with:
- Black background
- Centered song title in Inter font (all caps, white)
- Dynamic audio visualizer/equalizer that moves with the beat
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import librosa
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips
)
from moviepy.video.VideoClip import VideoClip
import tempfile


# YouTube Shorts dimensions (9:16 aspect ratio)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# Visual settings
BACKGROUND_COLOR = (0, 0, 0)  # Pure black
TEXT_COLOR = (255, 255, 255)  # Pure white
VISUALIZER_COLOR = (255, 255, 255)  # White bars

# Visualizer settings
NUM_BARS = 32
BAR_WIDTH = 20
BAR_GAP = 8
BAR_MAX_HEIGHT = 200
VISUALIZER_Y_OFFSET = 150  # Distance below center for visualizer


def get_inter_font(size: int):
    """
    Get Inter font. Falls back to system fonts if Inter is not available.
    """
    # Try to find Inter font in common locations
    font_paths = [
        "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
        "/usr/share/fonts/Inter-Bold.ttf",
        "/System/Library/Fonts/Inter-Bold.ttf",
        os.path.expanduser("~/.fonts/Inter-Bold.ttf"),
        os.path.join(os.path.dirname(__file__), "fonts", "Inter-Bold.ttf"),
        # Fallback system fonts
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)

    # Last resort: default font
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()


def compute_audio_features(audio_path: str, start_time: float, duration: float, fps: int = FPS):
    """
    Pre-compute audio features for visualization.

    Returns a 2D array where each row is a frame and contains
    the frequency band amplitudes for that moment in time.
    """
    # Load audio clip
    y, sr = librosa.load(audio_path, sr=22050, offset=start_time, duration=duration)

    # Compute mel spectrogram for frequency bands
    n_mels = NUM_BARS
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels, hop_length=512)

    # Convert to dB and normalize
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)
    mel_norm = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)

    # Get number of frames needed
    num_frames = int(duration * fps)

    # Resample to match video fps
    num_audio_frames = mel_norm.shape[1]
    frame_indices = np.linspace(0, num_audio_frames - 1, num_frames).astype(int)

    # Get amplitudes for each video frame
    frame_amplitudes = mel_norm[:, frame_indices].T  # Shape: (num_frames, num_bars)

    # Apply some smoothing between frames
    smoothed = np.zeros_like(frame_amplitudes)
    smoothed[0] = frame_amplitudes[0]
    alpha = 0.3  # Smoothing factor
    for i in range(1, len(frame_amplitudes)):
        smoothed[i] = alpha * frame_amplitudes[i] + (1 - alpha) * smoothed[i - 1]

    return smoothed


def create_frame(title: str, bar_amplitudes: np.ndarray, font) -> np.ndarray:
    """
    Create a single frame with title and visualizer bars.

    Args:
        title: Song title (will be displayed in ALL CAPS)
        bar_amplitudes: Array of amplitudes for each bar (0-1)
        font: PIL font object

    Returns:
        numpy array of the frame (RGB)
    """
    # Create black background
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw title (centered, all caps)
    title_upper = title.upper()

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), title_upper, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center position (slightly above center to make room for visualizer)
    text_x = (VIDEO_WIDTH - text_width) // 2
    text_y = (VIDEO_HEIGHT // 2) - text_height - 50

    # Draw text
    draw.text((text_x, text_y), title_upper, font=font, fill=TEXT_COLOR)

    # Draw visualizer bars below the title
    total_bar_width = NUM_BARS * BAR_WIDTH + (NUM_BARS - 1) * BAR_GAP
    start_x = (VIDEO_WIDTH - total_bar_width) // 2
    bar_y = VIDEO_HEIGHT // 2 + VISUALIZER_Y_OFFSET

    for i, amplitude in enumerate(bar_amplitudes):
        bar_height = int(amplitude * BAR_MAX_HEIGHT)
        bar_height = max(bar_height, 4)  # Minimum height

        x = start_x + i * (BAR_WIDTH + BAR_GAP)
        y_top = bar_y - bar_height // 2
        y_bottom = bar_y + bar_height // 2

        # Draw rounded rectangle bar
        draw.rounded_rectangle(
            [(x, y_top), (x + BAR_WIDTH, y_bottom)],
            radius=BAR_WIDTH // 4,
            fill=VISUALIZER_COLOR
        )

    return np.array(img)


def generate_video(
    audio_path: str,
    title: str,
    start_time: float,
    end_time: float,
    output_path: str
) -> str:
    """
    Generate the YouTube Short video.

    Args:
        audio_path: Path to the audio file
        title: Song title
        start_time: Start time of the clip in seconds
        end_time: End time of the clip in seconds
        output_path: Where to save the output video

    Returns:
        Path to the generated video
    """
    duration = end_time - start_time

    # Pre-compute audio features for visualization
    print("Analyzing audio for visualization...")
    audio_features = compute_audio_features(audio_path, start_time, duration)

    # Get font
    font = get_inter_font(72)  # Large, bold font

    print("Generating video frames...")

    # Create a function that returns the frame for a given time
    def make_frame(t):
        frame_idx = int(t * FPS)
        frame_idx = min(frame_idx, len(audio_features) - 1)
        return create_frame(title, audio_features[frame_idx], font)

    # Create video clip
    video_clip = VideoClip(make_frame, duration=duration)
    video_clip = video_clip.set_fps(FPS)

    # Add audio
    audio_clip = AudioFileClip(audio_path)
    audio_clip = audio_clip.subclip(start_time, end_time)
    video_clip = video_clip.set_audio(audio_clip)

    # Write output
    print("Encoding video...")
    video_clip.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        threads=4,
        logger=None  # Suppress moviepy output
    )

    # Clean up
    video_clip.close()
    audio_clip.close()

    print(f"Video saved to: {output_path}")
    return output_path


def generate_preview_thumbnail(title: str, output_path: str) -> str:
    """
    Generate a static preview thumbnail.

    Args:
        title: Song title
        output_path: Where to save the thumbnail

    Returns:
        Path to the thumbnail
    """
    font = get_inter_font(72)

    # Create a frame with medium bar heights for thumbnail
    bar_amplitudes = np.random.uniform(0.3, 0.8, NUM_BARS)
    frame = create_frame(title, bar_amplitudes, font)

    img = Image.fromarray(frame)
    img.save(output_path, 'PNG')

    return output_path
