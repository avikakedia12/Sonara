import { useState } from 'react'
import { braille } from '../api'
import { downloadFile } from '../downloadFile'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import { DownloadIcon, Spinner } from '../components/Icons'

const LOADING_MESSAGES = [
  'Reading the score…',
  'Reducing to a single voice…',
  'Laying out braille cells…',
]

export default function BraillePage() {
  const [source, setSource] = useState({ file: null })
  const [melodyOnly, setMelodyOnly] = useState(true)
  const [quantize, setQuantize] = useState('')
  const [partIndex, setPartIndex] = useState('0')
  const { loading, error, result, run } = useAsyncAction()
  const loadingMessage = useRotatingMessage(LOADING_MESSAGES, 3200, loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)
  const isAudio = Boolean(source.youtubeUrl) || (source.file && /\.(wav|mp3|flac|ogg|m4a|aiff?|aif)$/i.test(source.file.name))

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => braille(source, { partIndex, melodyOnly, quantize }))
  }

  return (
    <section>
      <h2>Braille</h2>
      <p className="page-blurb">
        Score (MusicXML/MIDI) or audio &rarr; Braille Music Code. For dense/audio-transcribed
        input, "melody only" collapses chords to a single top-note line, which the Braille
        engine handles far better than raw polyphony.
      </p>
      <form onSubmit={handleSubmit}>
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <label>
          Part index
          <input type="number" min="0" value={partIndex} onChange={(e) => setPartIndex(e.target.value)} />
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={melodyOnly} onChange={(e) => setMelodyOnly(e.target.checked)} />
          Melody only (recommended for dense/audio input)
        </label>
        <label>
          Braille rhythm quantization (comma-separated divisors, e.g. "4,3" -- leave blank to skip)
          <input type="text" value={quantize} onChange={(e) => setQuantize(e.target.value)} placeholder="e.g. 4,3" />
        </label>
        {isAudio && <p className="hint">Audio input detected -- will be transcribed first (adaptive thresholds).</p>}
        <button type="submit" disabled={loading || !hasSource}>
          {loading && <Spinner />}
          {loading ? 'Converting…' : 'Convert to Braille'}
        </button>
        {loading && <p className="loading-message">{loadingMessage}</p>}
      </form>

      {error && <p className="error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="⠿" text="Upload a score or audio file (or paste a YouTube link) to get Braille Music Code." />
      )}

      {result && (
        <div className="result">
          <ul className="result-meta">
            <li>{result.chunks_transcribed} / {result.chunks_total} chunks transcribed</li>
          </ul>
          {result.accuracy_note && <p className="accuracy-note">{result.accuracy_note}</p>}
          {result.failed_chunks?.length > 0 && (
            <p className="error">Failed chunks (beats): {JSON.stringify(result.failed_chunks)}</p>
          )}
          <div className="download-actions">
            <button type="button" className="download-button" onClick={() => downloadFile('braille.brl', result.brl)}>
              <DownloadIcon /> Download .brl
            </button>
            <button type="button" className="download-button" onClick={() => downloadFile('braille.brf', result.brf)}>
              <DownloadIcon /> Download .brf (embosser-ready)
            </button>
          </div>
          <h3>Braille (.brl)</h3>
          <pre className="braille-output">{result.brl}</pre>
        </div>
      )}
    </section>
  )
}
