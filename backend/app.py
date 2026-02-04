"""
Music Clip Extractor API
Flask backend for the YouTube Shorts music clip creator.
"""

import os
import uuid
import json
from flask import Flask, request, jsonify, send_file, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from audio_analyzer import analyze_audio, get_audio_waveform, get_beat_times
from video_generator import generate_video, generate_preview_thumbnail
from youtube_uploader import YouTubeUploader

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000', 'http://localhost:5173'])

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'outputs')
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac'}

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Store active sessions (in production, use Redis or database)
sessions = {}

# YouTube uploader instance
youtube_uploader = YouTubeUploader()


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


@app.route('/api/upload', methods=['POST'])
def upload_audio():
    """
    Upload an audio file and get the best clip analysis.

    Request:
        - file: Audio file (mp3, wav, etc.)
        - title: Song title

    Response:
        - session_id: Unique session ID
        - analysis: Best clip information
        - waveform: Waveform data for preview
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    title = request.form.get('title', 'Untitled')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Generate session ID
    session_id = str(uuid.uuid4())

    # Save file
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
    file.save(file_path)

    try:
        # Analyze audio
        analysis = analyze_audio(file_path)

        # Get waveform for preview
        waveform = get_audio_waveform(
            file_path,
            analysis.start_time,
            analysis.end_time,
            num_samples=100
        )

        # Get beat times for visualization sync
        beats = get_beat_times(file_path, analysis.start_time, analysis.end_time)

        # Store session
        sessions[session_id] = {
            'file_path': file_path,
            'title': title,
            'analysis': {
                'start_time': analysis.start_time,
                'end_time': analysis.end_time,
                'duration': analysis.duration,
                'score': analysis.score,
                'reason': analysis.reason
            },
            'video_path': None
        }

        return jsonify({
            'session_id': session_id,
            'title': title,
            'analysis': sessions[session_id]['analysis'],
            'waveform': waveform,
            'beats': beats
        })

    except Exception as e:
        # Clean up on error
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': str(e)}), 500


@app.route('/api/adjust-clip', methods=['POST'])
def adjust_clip():
    """
    Manually adjust the clip timing.

    Request:
        - session_id: Session ID
        - start_time: New start time
        - end_time: New end time
    """
    data = request.json
    session_id = data.get('session_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400

    if start_time is None or end_time is None:
        return jsonify({'error': 'start_time and end_time required'}), 400

    duration = end_time - start_time
    if duration < 10 or duration > 60:
        return jsonify({'error': 'Duration must be between 10 and 60 seconds'}), 400

    session = sessions[session_id]

    # Get new waveform
    waveform = get_audio_waveform(session['file_path'], start_time, end_time, num_samples=100)
    beats = get_beat_times(session['file_path'], start_time, end_time)

    # Update session
    session['analysis'] = {
        'start_time': start_time,
        'end_time': end_time,
        'duration': duration,
        'score': session['analysis']['score'],
        'reason': 'Manually adjusted'
    }

    return jsonify({
        'session_id': session_id,
        'analysis': session['analysis'],
        'waveform': waveform,
        'beats': beats
    })


@app.route('/api/generate-video', methods=['POST'])
def generate_video_endpoint():
    """
    Generate the video with visualizer.

    Request:
        - session_id: Session ID

    Response:
        - video_url: URL to preview the video
    """
    data = request.json
    session_id = data.get('session_id')

    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400

    session = sessions[session_id]

    try:
        # Generate video
        output_path = os.path.join(OUTPUT_FOLDER, f"{session_id}.mp4")

        generate_video(
            audio_path=session['file_path'],
            title=session['title'],
            start_time=session['analysis']['start_time'],
            end_time=session['analysis']['end_time'],
            output_path=output_path
        )

        session['video_path'] = output_path

        return jsonify({
            'session_id': session_id,
            'video_url': f'/api/video/{session_id}',
            'download_url': f'/api/download/{session_id}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/<session_id>', methods=['GET'])
def get_video(session_id):
    """Serve the generated video for preview."""
    if session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 404

    video_path = sessions[session_id].get('video_path')
    if not video_path or not os.path.exists(video_path):
        return jsonify({'error': 'Video not generated yet'}), 404

    return send_file(video_path, mimetype='video/mp4')


@app.route('/api/download/<session_id>', methods=['GET'])
def download_video(session_id):
    """Download the generated video."""
    if session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 404

    session = sessions[session_id]
    video_path = session.get('video_path')

    if not video_path or not os.path.exists(video_path):
        return jsonify({'error': 'Video not generated yet'}), 404

    filename = f"{session['title']}_short.mp4"
    return send_file(video_path, mimetype='video/mp4', as_attachment=True, download_name=filename)


# YouTube OAuth endpoints
@app.route('/api/youtube/status', methods=['GET'])
def youtube_status():
    """Check YouTube connection status."""
    try:
        if youtube_uploader.is_authenticated():
            channel = youtube_uploader.get_channel_info()
            return jsonify({
                'connected': True,
                'channel': channel
            })
    except Exception:
        pass

    return jsonify({'connected': False})


@app.route('/api/youtube/connect', methods=['GET'])
def youtube_connect():
    """Start YouTube OAuth flow."""
    try:
        auth_url = youtube_uploader.get_auth_url()
        return jsonify({'auth_url': auth_url})
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    """Handle YouTube OAuth callback."""
    # Get the full URL for the callback
    authorization_response = request.url

    try:
        youtube_uploader.handle_oauth_callback(authorization_response)
        # Redirect back to the frontend
        return redirect('http://localhost:3000?youtube_connected=true')
    except Exception as e:
        return redirect(f'http://localhost:3000?youtube_error={str(e)}')


@app.route('/api/youtube/disconnect', methods=['POST'])
def youtube_disconnect():
    """Disconnect YouTube account."""
    youtube_uploader.disconnect()
    return jsonify({'disconnected': True})


@app.route('/api/publish', methods=['POST'])
def publish_to_youtube():
    """
    Publish the video to YouTube.

    Request:
        - session_id: Session ID
        - privacy: 'public', 'unlisted', or 'private'
        - description: Optional video description
        - tags: Optional list of tags
    """
    data = request.json
    session_id = data.get('session_id')
    privacy = data.get('privacy', 'private')
    description = data.get('description', '')
    tags = data.get('tags', [])

    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400

    session = sessions[session_id]
    video_path = session.get('video_path')

    if not video_path or not os.path.exists(video_path):
        return jsonify({'error': 'Video not generated yet'}), 400

    if not youtube_uploader.is_authenticated():
        return jsonify({'error': 'YouTube not connected'}), 401

    try:
        # Build title and description
        title = f"{session['title']} #Shorts"
        if not description:
            description = f"Music clip from {session['title']}\n\n#Shorts #Music"

        # Add default tags
        default_tags = ['Shorts', 'Music', 'MusicClip']
        all_tags = list(set(default_tags + tags))

        result = youtube_uploader.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=all_tags,
            privacy_status=privacy
        )

        return jsonify({
            'success': True,
            'video_id': result['video_id'],
            'url': result['url'],
            'privacy': privacy
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """Clean up session files."""
    if session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 404

    session = sessions[session_id]

    # Remove files
    if session.get('file_path') and os.path.exists(session['file_path']):
        os.remove(session['file_path'])
    if session.get('video_path') and os.path.exists(session['video_path']):
        os.remove(session['video_path'])

    # Remove session
    del sessions[session_id]

    return jsonify({'cleaned': True})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
