import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'

// Types
interface Analysis {
  start_time: number
  end_time: number
  duration: number
  score: number
  reason: string
}

interface Session {
  session_id: string
  title: string
  analysis: Analysis
  waveform: number[]
}

interface YouTubeChannel {
  id: string
  title: string
  thumbnail: string
  subscriber_count: string
}

type Step = 'upload' | 'preview' | 'publish' | 'done'
type Privacy = 'public' | 'unlisted' | 'private'

function App() {
  const [step, setStep] = useState<Step>('upload')
  const [session, setSession] = useState<Session | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [youtubeChannel, setYoutubeChannel] = useState<YouTubeChannel | null>(null)
  const [privacy, setPrivacy] = useState<Privacy>('private')
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null)

  // Form state
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)

  // Loading states
  const [uploading, setUploading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [publishing, setPublishing] = useState(false)

  // Error state
  const [error, setError] = useState<string | null>(null)

  // Check YouTube connection on mount
  useEffect(() => {
    checkYouTubeStatus()

    // Check for OAuth callback
    const params = new URLSearchParams(window.location.search)
    if (params.get('youtube_connected') === 'true') {
      checkYouTubeStatus()
      window.history.replaceState({}, '', '/')
    }
    if (params.get('youtube_error')) {
      setError(`YouTube connection failed: ${params.get('youtube_error')}`)
      window.history.replaceState({}, '', '/')
    }
  }, [])

  const checkYouTubeStatus = async () => {
    try {
      const response = await axios.get('/api/youtube/status')
      if (response.data.connected) {
        setYoutubeChannel(response.data.channel)
      } else {
        setYoutubeChannel(null)
      }
    } catch {
      setYoutubeChannel(null)
    }
  }

  const connectYouTube = async () => {
    try {
      const response = await axios.get('/api/youtube/connect')
      window.location.href = response.data.auth_url
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message :
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Failed to connect to YouTube'
      setError(errorMessage)
    }
  }

  const disconnectYouTube = async () => {
    try {
      await axios.post('/api/youtube/disconnect')
      setYoutubeChannel(null)
    } catch {
      // Ignore errors
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type.startsWith('audio/')) {
      setFile(droppedFile)
      if (!title) {
        // Extract title from filename
        const name = droppedFile.name.replace(/\.[^/.]+$/, '')
        setTitle(name)
      }
    }
  }, [title])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      if (!title) {
        const name = selectedFile.name.replace(/\.[^/.]+$/, '')
        setTitle(name)
      }
    }
  }

  const handleUpload = async () => {
    if (!file || !title) return

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title)

      const response = await axios.post('/api/upload', formData)
      setSession(response.data)
      setStep('preview')
    } catch (err: unknown) {
      const errorMessage = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Upload failed'
      setError(errorMessage)
    } finally {
      setUploading(false)
    }
  }

  const handleGenerateVideo = async () => {
    if (!session) return

    setGenerating(true)
    setError(null)

    try {
      const response = await axios.post('/api/generate-video', {
        session_id: session.session_id
      })
      setVideoUrl(response.data.video_url)
    } catch (err: unknown) {
      const errorMessage = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Video generation failed'
      setError(errorMessage)
    } finally {
      setGenerating(false)
    }
  }

  const handlePublish = async () => {
    if (!session || !youtubeChannel) return

    setPublishing(true)
    setError(null)

    try {
      const response = await axios.post('/api/publish', {
        session_id: session.session_id,
        privacy
      })
      setPublishedUrl(response.data.url)
      setStep('done')
    } catch (err: unknown) {
      const errorMessage = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Publishing failed'
      setError(errorMessage)
    } finally {
      setPublishing(false)
    }
  }

  const handleStartOver = async () => {
    if (session) {
      try {
        await axios.delete(`/api/cleanup/${session.session_id}`)
      } catch {
        // Ignore cleanup errors
      }
    }
    setSession(null)
    setVideoUrl(null)
    setPublishedUrl(null)
    setFile(null)
    setTitle('')
    setStep('upload')
    setError(null)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <>
      <header className="header">
        <div className="container">
          <h1>Music Clip Extractor</h1>
        </div>
      </header>

      <main className="main">
        <div className="container">
          {/* Steps indicator */}
          <div className="steps">
            <div className={`step ${step === 'upload' ? 'active' : ''} ${['preview', 'publish', 'done'].includes(step) ? 'completed' : ''}`} />
            <div className={`step ${step === 'preview' ? 'active' : ''} ${['publish', 'done'].includes(step) ? 'completed' : ''}`} />
            <div className={`step ${step === 'publish' ? 'active' : ''} ${step === 'done' ? 'completed' : ''}`} />
            <div className={`step ${step === 'done' ? 'active' : ''}`} />
          </div>

          {error && (
            <div className="status error">{error}</div>
          )}

          {/* Step 1: Upload */}
          {step === 'upload' && (
            <div className="card">
              <div className="card-title">Upload Music</div>

              <div
                className={`upload-area ${dragOver ? 'dragover' : ''}`}
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => document.getElementById('file-input')?.click()}
              >
                <div className="upload-icon">♪</div>
                <div className="upload-text">
                  {file ? file.name : 'Drop your music file here'}
                </div>
                <div className="upload-hint">
                  MP3, WAV, OGG, M4A, FLAC, AAC
                </div>
                <input
                  id="file-input"
                  type="file"
                  accept="audio/*"
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
              </div>

              <div className="input-group" style={{ marginTop: 24 }}>
                <label className="input-label">Song Title</label>
                <input
                  className="input"
                  type="text"
                  placeholder="Enter the song title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              <button
                className="btn btn-primary btn-full"
                onClick={handleUpload}
                disabled={!file || !title || uploading}
              >
                {uploading ? (
                  <>
                    <span className="spinner" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze & Find Best Clip'
                )}
              </button>
            </div>
          )}

          {/* Step 2: Preview */}
          {step === 'preview' && session && (
            <>
              <div className="card">
                <div className="card-title">AI Analysis Result</div>

                <div className="analysis-result">
                  <div className="stat">
                    <div className="stat-label">Start Time</div>
                    <div className="stat-value">{formatTime(session.analysis.start_time)}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">End Time</div>
                    <div className="stat-value">{formatTime(session.analysis.end_time)}</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">Duration</div>
                    <div className="stat-value">{session.analysis.duration.toFixed(1)}s</div>
                  </div>
                  <div className="stat">
                    <div className="stat-label">Confidence</div>
                    <div className="stat-value">{Math.round(session.analysis.score * 100)}%</div>
                  </div>
                </div>

                <div className="stat" style={{ marginBottom: 24 }}>
                  <div className="stat-label">Why this clip?</div>
                  <div className="stat-value small">{session.analysis.reason}</div>
                </div>

                {/* Waveform visualization */}
                <div className="waveform-container">
                  <div className="waveform">
                    {session.waveform.map((amplitude, i) => (
                      <div
                        key={i}
                        className="waveform-bar"
                        style={{ height: `${Math.max(amplitude * 100, 10)}%` }}
                      />
                    ))}
                  </div>
                </div>

                {!videoUrl ? (
                  <button
                    className="btn btn-primary btn-full"
                    onClick={handleGenerateVideo}
                    disabled={generating}
                  >
                    {generating ? (
                      <>
                        <span className="spinner" />
                        Generating Video...
                      </>
                    ) : (
                      'Generate Preview Video'
                    )}
                  </button>
                ) : (
                  <>
                    <div className="video-preview">
                      <video controls src={videoUrl} />
                    </div>

                    <div className="btn-group">
                      <button
                        className="btn btn-secondary"
                        onClick={handleStartOver}
                      >
                        Start Over
                      </button>
                      <button
                        className="btn btn-primary"
                        onClick={() => setStep('publish')}
                      >
                        Approve & Continue
                      </button>
                    </div>
                  </>
                )}
              </div>
            </>
          )}

          {/* Step 3: Publish */}
          {step === 'publish' && session && (
            <div className="card">
              <div className="card-title">Publish to YouTube</div>

              {/* YouTube connection status */}
              {youtubeChannel ? (
                <div className="youtube-status connected">
                  <img
                    className="youtube-avatar"
                    src={youtubeChannel.thumbnail}
                    alt={youtubeChannel.title}
                  />
                  <div className="youtube-info">
                    <div className="youtube-channel">{youtubeChannel.title}</div>
                    <div className="youtube-subs">
                      {parseInt(youtubeChannel.subscriber_count).toLocaleString()} subscribers
                    </div>
                  </div>
                  <button className="btn btn-secondary" onClick={disconnectYouTube}>
                    Disconnect
                  </button>
                </div>
              ) : (
                <div className="youtube-status">
                  <div className="youtube-info">
                    <div className="youtube-channel">YouTube not connected</div>
                    <div className="youtube-subs">Connect to publish your Short</div>
                  </div>
                  <button className="btn btn-primary" onClick={connectYouTube}>
                    Connect YouTube
                  </button>
                </div>
              )}

              {/* Privacy selector */}
              <div className="card-title" style={{ marginTop: 24 }}>Privacy</div>
              <div className="privacy-selector">
                <div
                  className={`privacy-option ${privacy === 'public' ? 'selected' : ''}`}
                  onClick={() => setPrivacy('public')}
                >
                  <div className="privacy-option-label">Public</div>
                  <div className="privacy-option-desc">Anyone can watch</div>
                </div>
                <div
                  className={`privacy-option ${privacy === 'unlisted' ? 'selected' : ''}`}
                  onClick={() => setPrivacy('unlisted')}
                >
                  <div className="privacy-option-label">Unlisted</div>
                  <div className="privacy-option-desc">Only with link</div>
                </div>
                <div
                  className={`privacy-option ${privacy === 'private' ? 'selected' : ''}`}
                  onClick={() => setPrivacy('private')}
                >
                  <div className="privacy-option-label">Private</div>
                  <div className="privacy-option-desc">Only you</div>
                </div>
              </div>

              <div className="btn-group">
                <button
                  className="btn btn-secondary"
                  onClick={() => setStep('preview')}
                >
                  Back
                </button>
                <button
                  className="btn btn-success"
                  onClick={handlePublish}
                  disabled={!youtubeChannel || publishing}
                >
                  {publishing ? (
                    <>
                      <span className="spinner" />
                      Publishing...
                    </>
                  ) : (
                    'Publish to YouTube'
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Done */}
          {step === 'done' && (
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 64, marginBottom: 24 }}>✓</div>
              <h2 style={{ marginBottom: 16 }}>Published Successfully!</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
                Your music Short has been uploaded to YouTube.
              </p>

              {publishedUrl && (
                <a
                  href={publishedUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary"
                  style={{ marginBottom: 16 }}
                >
                  View on YouTube
                </a>
              )}

              <button
                className="btn btn-secondary btn-full"
                onClick={handleStartOver}
              >
                Create Another Short
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  )
}

export default App
