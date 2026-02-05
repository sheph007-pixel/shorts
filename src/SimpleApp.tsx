import { useState, useEffect } from 'react'
import axios from 'axios'

// Types
interface YouTubeChannel {
  id: string
  title: string
  thumbnail: string
  subscriber_count: string
}

interface ShortSession {
  session_id: string
  video_info: {
    title: string
    duration: number
  }
  clip_info: {
    start_time: number
    duration: number
    title: string
  }
  video_url: string
  download_url: string
}

type Privacy = 'public' | 'unlisted' | 'private'

const API_BASE = import.meta.env.VITE_API_URL || ''

function SimpleApp() {
  // State
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [customTitle, setCustomTitle] = useState('')
  const [duration, setDuration] = useState(30)
  const [youtubeChannel, setYoutubeChannel] = useState<YouTubeChannel | null>(null)
  const [session, setSession] = useState<ShortSession | null>(null)
  const [privacy, setPrivacy] = useState<Privacy>('private')
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null)

  // Loading states
  const [creating, setCreating] = useState(false)
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
      const response = await axios.get(`${API_BASE}/api/youtube/status`)
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
      const response = await axios.get(`${API_BASE}/api/youtube/connect`)
      window.location.href = response.data.auth_url
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message :
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Failed to connect to YouTube'
      setError(errorMessage)
    }
  }

  const disconnectYouTube = async () => {
    try {
      await axios.post(`${API_BASE}/api/youtube/disconnect`)
      setYoutubeChannel(null)
    } catch {
      // Ignore errors
    }
  }

  const handleCreateShort = async () => {
    if (!youtubeUrl) return

    setCreating(true)
    setError(null)
    setSession(null)

    try {
      const response = await axios.post(`${API_BASE}/api/youtube-to-short`, {
        url: youtubeUrl,
        title: customTitle || undefined,
        duration: duration
      })

      setSession(response.data)
    } catch (err: unknown) {
      const errorMessage = (err as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Failed to create short'
      setError(errorMessage)
    } finally {
      setCreating(false)
    }
  }

  const handlePublish = async () => {
    if (!session || !youtubeChannel) return

    setPublishing(true)
    setError(null)

    try {
      const response = await axios.post(`${API_BASE}/api/publish`, {
        session_id: session.session_id,
        privacy
      })
      setPublishedUrl(response.data.url)
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
        await axios.delete(`${API_BASE}/api/cleanup/${session.session_id}`)
      } catch {
        // Ignore cleanup errors
      }
    }
    setSession(null)
    setPublishedUrl(null)
    setYoutubeUrl('')
    setCustomTitle('')
    setDuration(30)
    setError(null)
  }

  return (
    <>
      <header className="header">
        <div className="container">
          <h1>YouTube Shorts Creator</h1>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', margin: '8px 0 0' }}>
            Convert any YouTube video into a vertical short
          </p>
        </div>
      </header>

      <main className="main">
        <div className="container">
          {error && (
            <div className="status error">{error}</div>
          )}

          {/* YouTube connection status */}
          <div className="card" style={{ marginBottom: 24 }}>
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
                  <div className="youtube-subs">Connect to publish your shorts</div>
                </div>
                <button className="btn btn-primary" onClick={connectYouTube}>
                  Connect YouTube
                </button>
              </div>
            )}
          </div>

          {!publishedUrl ? (
            <>
              {/* Input form */}
              <div className="card">
                <div className="card-title">Create Short from YouTube Video</div>

                <div className="input-group">
                  <label className="input-label">YouTube URL</label>
                  <input
                    className="input"
                    type="text"
                    placeholder="https://www.youtube.com/watch?v=..."
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                  />
                </div>

                <div className="input-group">
                  <label className="input-label">Custom Title (optional)</label>
                  <input
                    className="input"
                    type="text"
                    placeholder="Leave blank to use video title"
                    value={customTitle}
                    onChange={(e) => setCustomTitle(e.target.value)}
                  />
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                    Bold white text will be displayed on the short
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label">Duration: {duration} seconds</label>
                  <input
                    type="range"
                    min="20"
                    max="40"
                    value={duration}
                    onChange={(e) => setDuration(parseInt(e.target.value))}
                    style={{ width: '100%' }}
                  />
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                    Recommended: 20-40 seconds for YouTube Shorts
                  </div>
                </div>

                <button
                  className="btn btn-primary btn-full"
                  onClick={handleCreateShort}
                  disabled={!youtubeUrl || creating}
                >
                  {creating ? (
                    <>
                      <span className="spinner" />
                      Creating Short...
                    </>
                  ) : (
                    'Create Short'
                  )}
                </button>
              </div>

              {/* Preview */}
              {session && (
                <div className="card">
                  <div className="card-title">Preview</div>

                  <div className="analysis-result">
                    <div className="stat">
                      <div className="stat-label">Source Video</div>
                      <div className="stat-value small">{session.video_info.title}</div>
                    </div>
                    <div className="stat">
                      <div className="stat-label">Clip Duration</div>
                      <div className="stat-value">{session.clip_info.duration}s</div>
                    </div>
                  </div>

                  <div className="video-preview">
                    <video controls src={`${API_BASE}${session.video_url}`} />
                  </div>

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
                      onClick={handleStartOver}
                    >
                      Start Over
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
            </>
          ) : (
            /* Success */
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 64, marginBottom: 24 }}>✓</div>
              <h2 style={{ marginBottom: 16 }}>Published Successfully!</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
                Your YouTube Short has been uploaded.
              </p>

              <a
                href={publishedUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ marginBottom: 16 }}
              >
                View on YouTube
              </a>

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

export default SimpleApp
