# YouTube Shorts Creator

Simple application to convert YouTube videos into vertical shorts and automatically post them to your YouTube channel.

## Features

- 🎥 Download any YouTube video
- ✂️ Auto-extract 20-40 second clips
- 📱 Convert to vertical format (9:16)
- 📝 Add bold white text overlay on black background
- 📤 Publish directly to YouTube

## Setup

### Prerequisites

- Python 3.9+
- Node.js 16+
- FFmpeg installed

### Backend Setup

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Create `backend/.env` file (if needed):
```
# No environment variables required for basic use
```

3. Set up YouTube API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Download `client_secrets.json` and place in `backend/` directory

4. Start the backend:
```bash
python app.py
```

Backend will run on `http://localhost:5000`

### Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Start the frontend:
```bash
npm run dev
```

Frontend will run on `http://localhost:5173`

## Usage

1. **Connect YouTube**
   - Click "Connect YouTube" button
   - Authorize the application

2. **Create Short**
   - Enter a YouTube URL
   - (Optional) Add custom title text
   - Adjust duration (20-40 seconds)
   - Click "Create Short"

3. **Preview & Publish**
   - Preview the generated vertical short
   - Select privacy setting (Public/Unlisted/Private)
   - Click "Publish to YouTube"

## How It Works

1. **Download**: Uses `yt-dlp` to download the YouTube video
2. **Extract**: Automatically selects a good clip section (or you can specify start time)
3. **Convert**: Uses FFmpeg via `moviepy` to:
   - Resize to 1080x1920 (9:16 aspect ratio)
   - Add black background
   - Add bold white text overlay
4. **Upload**: Publishes to YouTube using YouTube Data API v3

## API Endpoints

### Create Short
```
POST /api/youtube-to-short
{
  "url": "https://www.youtube.com/watch?v=...",
  "title": "Custom Title (optional)",
  "duration": 30,
  "start_time": 10 (optional)
}
```

### Publish to YouTube
```
POST /api/publish
{
  "session_id": "...",
  "privacy": "public|unlisted|private"
}
```

## Tips

- Keep titles short and bold for maximum impact
- 30 seconds is the sweet spot for engagement
- Start with "private" to review before going public
- Use public domain or properly licensed content only

## License

MIT
