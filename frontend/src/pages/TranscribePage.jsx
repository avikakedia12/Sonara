import { useState } from 'react'
import { transcribe } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import SheetMusic from '../components/SheetMusic'
import FileDrop from '../components/FileDrop'
import { Spinner } from '../components/Icons'

export default function TranscribePage() {
  const [file, setFile] = useState(null)
  const [quantize, setQuantize] = useState('4')
  const [title, setTitle] = useState('')
  const { loading, error, result, run } = useAsyncAction()

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!file) return
    run(() => transcribe(file, { quantize, title }))
  }

  return (
    <section>
      <h2>Transcribe</h2>
      <p className="page-blurb">
        Audio &rarr; notated score. Best-effort ML transcription -- see the accuracy note
        in the result below.
      </p>
      <form onSubmit={handleSubmit}>
        <FileDrop file={file} onChange={setFile} accept="audio/*" label="Drop an audio file" />
        <label>
          Quantize (beat-grid subdivisions, e.g. 4 = 16th notes)
          <input type="number" min="1" value={quantize} onChange={(e) => setQuantize(e.target.value)} />
        </label>
        <label>
          Title (optional)
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="defaults to filename" />
        </label>
        <button type="submit" disabled={loading || !file}>
          {loading && <Spinner />}
          {loading ? 'Transcribing…' : 'Transcribe'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

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
