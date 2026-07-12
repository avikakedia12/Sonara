import { useState } from 'react'
import { describe } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import FileDrop from '../components/FileDrop'
import { Spinner } from '../components/Icons'

export default function DescribePage() {
  const [file, setFile] = useState(null)
  const [level, setLevel] = useState('standard')
  const [speak, setSpeak] = useState(false)
  const { loading, error, result, run } = useAsyncAction()

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!file) return
    run(() => describe(file, { level, speak }))
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
        <FileDrop file={file} onChange={setFile} label="Drop a score or audio file" />
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
        <button type="submit" disabled={loading || !file}>
          {loading && <Spinner />}
          {loading ? 'Describing…' : 'Describe'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

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
