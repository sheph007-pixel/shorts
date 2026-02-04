"""
Audio Analyzer Module
Uses librosa to analyze music and find the best 10-20 second clip for a YouTube Short.
"""

import librosa
import numpy as np
from dataclasses import dataclass


@dataclass
class ClipResult:
    """Result of the best clip analysis."""
    start_time: float
    end_time: float
    duration: float
    score: float
    reason: str


def analyze_audio(file_path: str, min_duration: float = 10.0, max_duration: float = 20.0) -> ClipResult:
    """
    Analyze an audio file and find the best clip for a YouTube Short.

    The algorithm considers:
    1. Energy levels - finds sections with high energy
    2. Beat strength - prefers sections with strong, consistent beats
    3. Spectral contrast - looks for interesting/dynamic sections
    4. Onset density - prefers sections with good rhythmic activity

    Args:
        file_path: Path to the audio file
        min_duration: Minimum clip duration in seconds (default 10)
        max_duration: Maximum clip duration in seconds (default 20)

    Returns:
        ClipResult with the best clip information
    """
    # Load audio file
    y, sr = librosa.load(file_path, sr=22050)
    duration = librosa.get_duration(y=y, sr=sr)

    # If the song is shorter than max_duration, use the whole thing
    if duration <= max_duration:
        return ClipResult(
            start_time=0.0,
            end_time=duration,
            duration=duration,
            score=1.0,
            reason="Full track used (shorter than max duration)"
        )

    # Calculate features for analysis
    # 1. RMS Energy - how loud/energetic each section is
    rms = librosa.feature.rms(y=y)[0]

    # 2. Spectral centroid - brightness of sound
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]

    # 3. Beat tracking
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # 4. Onset strength - rhythmic activity
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # 5. Spectral contrast - dynamic range across frequency bands
    spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    contrast_mean = np.mean(spectral_contrast, axis=0)

    # Convert features to time-aligned scores
    hop_length = 512
    frame_duration = hop_length / sr
    num_frames = len(rms)

    # Normalize features
    rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-8)
    centroid_norm = (spectral_centroid - np.min(spectral_centroid)) / (np.max(spectral_centroid) - np.min(spectral_centroid) + 1e-8)
    onset_norm = (onset_env - np.min(onset_env)) / (np.max(onset_env) - np.min(onset_env) + 1e-8)
    contrast_norm = (contrast_mean - np.min(contrast_mean)) / (np.max(contrast_mean) - np.min(contrast_mean) + 1e-8)

    # Combined score for each frame
    # Weight: energy (40%), onset strength (30%), spectral contrast (20%), brightness (10%)
    combined_score = (
        0.4 * rms_norm +
        0.3 * onset_norm[:len(rms_norm)] +
        0.2 * contrast_norm[:len(rms_norm)] +
        0.1 * centroid_norm[:len(rms_norm)]
    )

    # Find the best window
    target_duration = (min_duration + max_duration) / 2  # Aim for middle of range
    window_frames = int(target_duration / frame_duration)

    best_score = -1
    best_start_frame = 0

    # Slide window across the song
    for start_frame in range(0, len(combined_score) - window_frames, int(0.5 / frame_duration)):  # 0.5s steps
        window_score = np.mean(combined_score[start_frame:start_frame + window_frames])

        # Bonus for starting near a beat
        start_time = start_frame * frame_duration
        beat_distances = np.abs(beat_times - start_time)
        if len(beat_distances) > 0:
            min_beat_dist = np.min(beat_distances)
            beat_bonus = 0.1 * (1 - min(min_beat_dist / 0.5, 1))  # Bonus if within 0.5s of beat
            window_score += beat_bonus

        # Slight penalty for very beginning and end of song (often fade in/out)
        position_in_song = start_time / duration
        if position_in_song < 0.1 or position_in_song > 0.85:
            window_score *= 0.8

        if window_score > best_score:
            best_score = window_score
            best_start_frame = start_frame

    # Convert to time
    start_time = best_start_frame * frame_duration

    # Snap to nearest beat if possible
    if len(beat_times) > 0:
        beat_distances = np.abs(beat_times - start_time)
        nearest_beat_idx = np.argmin(beat_distances)
        if beat_distances[nearest_beat_idx] < 0.3:  # Within 300ms
            start_time = beat_times[nearest_beat_idx]

    # Ensure we don't exceed song duration
    end_time = min(start_time + target_duration, duration)
    actual_duration = end_time - start_time

    # If we're too short, adjust start time back
    if actual_duration < min_duration and start_time > 0:
        start_time = max(0, end_time - target_duration)
        actual_duration = end_time - start_time

    # Determine reason for selection
    start_frame = int(start_time / frame_duration)
    end_frame = min(start_frame + window_frames, len(rms_norm))

    avg_energy = np.mean(rms_norm[start_frame:end_frame])
    avg_onset = np.mean(onset_norm[start_frame:end_frame])

    if avg_energy > 0.7:
        reason = "High energy section with strong dynamics"
    elif avg_onset > 0.6:
        reason = "Rhythmically active section with good beat presence"
    else:
        reason = "Best overall balance of energy and musical interest"

    return ClipResult(
        start_time=round(start_time, 2),
        end_time=round(end_time, 2),
        duration=round(actual_duration, 2),
        score=round(best_score, 3),
        reason=reason
    )


def get_audio_waveform(file_path: str, start_time: float, end_time: float, num_samples: int = 100) -> list:
    """
    Get waveform data for visualization.

    Args:
        file_path: Path to audio file
        start_time: Start time in seconds
        end_time: End time in seconds
        num_samples: Number of amplitude samples to return

    Returns:
        List of normalized amplitude values (0-1)
    """
    y, sr = librosa.load(file_path, sr=22050, offset=start_time, duration=end_time - start_time)

    # Get RMS energy for smoother visualization
    rms = librosa.feature.rms(y=y)[0]

    # Resample to desired number of points
    indices = np.linspace(0, len(rms) - 1, num_samples).astype(int)
    samples = rms[indices]

    # Normalize to 0-1
    samples = (samples - np.min(samples)) / (np.max(samples) - np.min(samples) + 1e-8)

    return samples.tolist()


def get_beat_times(file_path: str, start_time: float, end_time: float) -> list:
    """
    Get beat times within a specific section for visualization sync.

    Args:
        file_path: Path to audio file
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        List of beat times (relative to clip start)
    """
    y, sr = librosa.load(file_path, sr=22050, offset=start_time, duration=end_time - start_time)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    return beat_times.tolist()
