import { useState } from 'react'
import { transpose, INSTRUMENTS } from '../api'
import { downloadFile } from '../downloadFile'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import SheetMusic from '../components/SheetMusic'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import { DownloadIcon, Spinner } from '../components/Icons'

const LOADING_MESSAGES = [
  'Reading the score…',
  'Converting to concert pitch…',
  'Transposing for the target instrument…',
  'Checking playable range…',
]

export default function TransposePage() {
  const [source, setSource] = useState({ file: null })
  const [targetInstrument, setTargetInstrument] = useState('clarinet')
  const { loading, error, result, run } = useAsyncAction()
  const loadingMessage = useRotatingMessage(LOADING_MESSAGES, 3200, loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => transpose(source, targetInstrument))
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
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <label>
          Target instrument
          <select value={targetInstrument} onChange={(e) => setTargetInstrument(e.target.value)}>
            {INSTRUMENTS.map((name) => (
              <option key={name} value={name}>{name.replace('_', ' ')}</option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={loading || !hasSource}>
          {loading && <Spinner />}
          {loading ? 'Transposing…' : 'Transpose'}
        </button>
        {loading && <p className="loading-message">{loadingMessage}</p>}
      </form>

      {error && <p className="error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="🎻" text="Upload a score or audio file (or paste a YouTube link) and pick a target instrument." />
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
          <div className="download-actions">
            <button
              type="button"
              className="download-button"
              onClick={() => downloadFile(`transposed_${result.target_instrument}.musicxml`, result.musicxml, 'application/vnd.recordare.musicxml+xml')}
            >
              <DownloadIcon /> Download MusicXML
            </button>
          </div>
          <SheetMusic pages={result.sheet_music_svg} />
        </div>
      )}
    </section>
  )
}
