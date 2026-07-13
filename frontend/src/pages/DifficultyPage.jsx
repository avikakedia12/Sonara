import { useState } from 'react'
import { difficulty } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import { Spinner } from '../components/Icons'

const LOADING_MESSAGES = [
  'Reading the score…',
  'Measuring rhythm, range, and leaps…',
  'Weighing up the difficulty…',
]

const FACTOR_LABELS = {
  rhythm: 'Rhythm',
  interval_leaps: 'Melodic leaps',
  chord_density: 'Chord density',
  tempo_density: 'Tempo & pace',
  pitch_range: 'Pitch range',
  key_complexity: 'Key signature',
  time_signature: 'Time signature',
}

function FactorMeter({ name, score, detail }) {
  const label = FACTOR_LABELS[name] || name
  return (
    <div>
      <div className="difficulty-factor-row">
        <span className="difficulty-factor-label">{label}</span>
        <span className="difficulty-factor-track" role="presentation">
          <span className="difficulty-factor-fill" style={{ width: `${(score / 10) * 100}%` }} />
        </span>
        <span className="difficulty-factor-value">{score.toFixed(1)}/10</span>
      </div>
      <p className="difficulty-factor-detail">{detail}</p>
    </div>
  )
}

export default function DifficultyPage() {
  const [source, setSource] = useState({ file: null })
  const { loading, error, result, run } = useAsyncAction()
  const loadingMessage = useRotatingMessage(LOADING_MESSAGES, 3200, loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => difficulty(source))
  }

  return (
    <section>
      <h2>Difficulty</h2>
      <p className="page-blurb">
        Score (MusicXML/MIDI) or audio &rarr; an estimated performance difficulty per part, with
        the exact numbers behind the rating -- fastest note value, pitch range, average melodic
        leap, chord density, key signature, and notes-per-second at the marked tempo. A
        deterministic, rule-based heuristic, not a certified grade level.
      </p>
      <form onSubmit={handleSubmit}>
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <button type="submit" disabled={loading || !hasSource}>
          {loading && <Spinner />}
          {loading ? 'Analyzing…' : 'Rate difficulty'}
        </button>
        {loading && <p className="loading-message">{loadingMessage}</p>}
      </form>

      {error && <p className="error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="🎚️" text="Upload a score or audio file (or paste a YouTube link) to estimate how hard it is to play." />
      )}

      {result && (
        <div className="result">
          {result.accuracy_note && <p className="accuracy-note">{result.accuracy_note}</p>}

          <div className="difficulty-headline">
            <div className="difficulty-score-value">
              {result.overall_score.toFixed(1)}
              <small>/10</small>
            </div>
            <span className="difficulty-level-badge">{result.overall_level}</span>
          </div>

          <p className="description-text">{result.summary}</p>

          <div className="difficulty-parts">
            {result.per_part.map((part) => (
              <div className="difficulty-part" key={part.name}>
                <div className="difficulty-part-header">
                  <h4>{part.name}</h4>
                  <span className="difficulty-part-score">{part.level} &middot; {part.score.toFixed(1)}/10</span>
                </div>
                <div className="difficulty-factors">
                  {Object.entries(part.factors).map(([name, factor]) => (
                    <FactorMeter key={name} name={name} score={factor.score} detail={factor.detail} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
