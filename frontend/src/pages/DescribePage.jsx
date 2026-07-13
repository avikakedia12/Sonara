import { useState } from 'react'
import { describe } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import { Spinner } from '../components/Icons'

const LOADING_MESSAGES = [
  'Reading the score…',
  'Estimating key and tempo…',
  'Composing the description…',
]

export default function DescribePage() {
  const [source, setSource] = useState({ file: null })
  const [level, setLevel] = useState('standard')
  const [speak, setSpeak] = useState(false)
  const { loading, error, result, run } = useAsyncAction()
  const loadingMessage = useRotatingMessage(LOADING_MESSAGES, 3200, loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => describe(source, { level, speak }))
  }

  const audioSrc = result?.audio_base64
    ? `data:audio/${result.audio_format};base64,${result.audio_base64}`
    : null

  return (
    <section>
      <h2>Describe</h2>
      <p className="page-blurb">
        Score (MusicXML/MIDI) or audio &rarr; a plain-text structural description (title, key,
        tempo, instrumentation, length) -- meant to orient a blind musician before reading the
        piece note-by-note. Optionally spoken aloud.
      </p>
      <form onSubmit={handleSubmit}>
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <label>
          Detail level
          <select value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="brief">Brief</option>
            <option value="standard">Standard</option>
            <option value="detailed">Detailed</option>
          </select>
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={speak} onChange={(e) => setSpeak(e.target.checked)} />
          Also render as speech (requires pyttsx3 installed server-side)
        </label>
        <button type="submit" disabled={loading || !hasSource}>
          {loading && <Spinner />}
          {loading ? 'Describing…' : 'Describe'}
        </button>
        {loading && <p className="loading-message">{loadingMessage}</p>}
      </form>

      {error && <p className="error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="📝" text="Upload a score or audio file (or paste a YouTube link) to get a structural description." />
      )}

      {result && (
        <div className="result">
          {result.accuracy_note && <p className="accuracy-note">{result.accuracy_note}</p>}
          <p className="description-text">{result.description}</p>
          {audioSrc && (
            <audio controls src={audioSrc} style={{ width: '100%', marginTop: '1.25rem' }}>
              Your browser doesn't support inline audio playback.
            </audio>
          )}
        </div>
      )}
    </section>
  )
}
