import { useState } from 'react'
import { transpose, INSTRUMENTS } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import SheetMusic from '../components/SheetMusic'
import FileDrop from '../components/FileDrop'
import EmptyState from '../components/EmptyState'
import { Spinner } from '../components/Icons'

const LOADING_MESSAGES = [
  'Reading the score…',
  'Converting to concert pitch…',
  'Transposing for the target instrument…',
  'Checking playable range…',
]

export default function TransposePage() {
  const [file, setFile] = useState(null)
  const [targetInstrument, setTargetInstrument] = useState('clarinet')
  const { loading, error, result, run } = useAsyncAction()
  const loadingMessage = useRotatingMessage(LOADING_MESSAGES, 3200, loading)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!file) return
    run(() => transpose(file, targetInstrument))
  }

  return (
    <section>
      <h2>Transpose</h2>
      <p className="page-blurb">
        Score (MusicXML/MIDI) or audio + a target instrument &rarr; a transposed score written
        for that instrument, range-checked against it. Out-of-range notes are flagged, never
        silently altered -- that's a judgment call for a human.
      </p>
      <form onSubmit={handleSubmit}>
        <FileDrop file={file} onChange={setFile} label="Drop a score or audio file" />
        <label>
          Target instrument
          <select value={targetInstrument} onChange={(e) => setTargetInstrument(e.target.value)}>
            {INSTRUMENTS.map((name) => (
              <option key={name} value={name}>{name.replace('_', ' ')}</option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={loading || !file}>
          {loading && <Spinner />}
          {loading ? 'Transposing…' : 'Transpose'}
        </button>
        {loading && <p className="loading-message">{loadingMessage}</p>}
      </form>

      {error && <p className="error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="🎻" text="Upload a score or audio file and pick a target instrument to transpose for." />
      )}

      {result && (
        <div className="result">
          <ul className="result-meta">
            <li>Target: {result.target_instrument}</li>
            <li>Range {result.playable_range?.low}&ndash;{result.playable_range?.high}</li>
          </ul>
          {result.accuracy_note && <p className="accuracy-note">{result.accuracy_note}</p>}
          {result.out_of_range_notes?.length > 0 && (
            <details>
              <summary>{result.out_of_range_notes.length} note(s) outside playable range (flagged, not altered)</summary>
              <ul className="out-of-range-list">
                {result.out_of_range_notes.map((n, i) => (
                  <li key={i}>beat {n.offset.toFixed(2)}: {n.pitch} ({n.direction} range)</li>
                ))}
              </ul>
            </details>
          )}
          <SheetMusic pages={result.sheet_music_svg} />
        </div>
      )}
    </section>
  )
}
