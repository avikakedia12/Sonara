import { useState } from 'react'
import { braille } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'

export default function BraillePage() {
  const [file, setFile] = useState(null)
  const [melodyOnly, setMelodyOnly] = useState(true)
  const [quantize, setQuantize] = useState('')
  const [partIndex, setPartIndex] = useState('0')
  const { loading, error, result, run } = useAsyncAction()

  const isAudio = file && /\.(wav|mp3|flac|ogg|m4a|aiff?|aif)$/i.test(file.name)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!file) return
    run(() => braille(file, { partIndex, melodyOnly, quantize }))
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
        <label>
          Score or audio file
          <input type="file" onChange={(e) => setFile(e.target.files[0])} required />
        </label>
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
        <button type="submit" disabled={loading || !file}>
          {loading ? 'Converting...' : 'Convert to Braille'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="result">
          <p>
            Chunks transcribed: {result.chunks_transcribed} / {result.chunks_total}
          </p>
          {result.accuracy_note && <p className="accuracy-note">{result.accuracy_note}</p>}
          {result.failed_chunks?.length > 0 && (
            <p className="error">Failed chunks (beats): {JSON.stringify(result.failed_chunks)}</p>
          )}
          <h3>Braille (.brl)</h3>
          <pre className="braille-output">{result.brl}</pre>
        </div>
      )}
    </section>
  )
}
