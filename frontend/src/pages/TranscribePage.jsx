import { useState } from 'react'
import { transcribe } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import SheetMusic from '../components/SheetMusic'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import { Spinner } from '../components/Icons'

const LOADING_MESSAGES = [
  'Listening to the audio…',
  'Detecting notes and onsets…',
  'Estimating tempo and polyphony…',
  'Engraving sheet music…',
]

export default function TranscribePage() {
  const [source, setSource] = useState({ file: null })
  const [quantize, setQuantize] = useState('4')
  const [title, setTitle] = useState('')
  const { loading, error, result, run } = useAsyncAction()
  const loadingMessage = useRotatingMessage(LOADING_MESSAGES, 3200, loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => transcribe(source, { quantize, title }))
  }

  return (
    <section>
      <h2>Transcribe</h2>
      <p className="page-blurb">
        Audio &rarr; notated score. Best-effort ML transcription -- see the accuracy note
        in the result below.
      </p>
      <form onSubmit={handleSubmit}>
        <AudioSourceInput source={source} onChange={setSource} accept="audio/*" label="Drop an audio file" />
        <label>
          Quantize (beat-grid subdivisions, e.g. 4 = 16th notes)
          <input type="number" min="1" value={quantize} onChange={(e) => setQuantize(e.target.value)} />
        </label>
        <label>
          Title (optional)
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="defaults to filename" />
        </label>
        <button type="submit" disabled={loading || !hasSource}>
          {loading && <Spinner />}
          {loading ? 'Transcribing…' : 'Transcribe'}
        </button>
        {loading && <p className="loading-message">{loadingMessage}</p>}
      </form>

      {error && <p className="error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="🎼" text="Upload a recording (or paste a YouTube link) to see it turned into notated sheet music." />
      )}

      {result && (
        <div className="result">
          <ul className="result-meta">
            <li>Polyphony {result.polyphony?.toFixed(2)}</li>
            <li>{result.tempo_bpm?.toFixed(1)} BPM</li>
            <li>onset {result.thresholds_used?.onset_threshold} / frame {result.thresholds_used?.frame_threshold}</li>
          </ul>
          <p className="accuracy-note">{result.accuracy_note}</p>
          <SheetMusic pages={result.sheet_music_svg} />
        </div>
      )}
    </section>
  )
}
