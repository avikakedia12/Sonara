import { useState } from 'react'
import { difficulty } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import { useSimulatedProgress } from '../hooks/useSimulatedProgress'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import LoadingProgress from '../components/LoadingProgress'
import { Spinner } from '../components/Icons'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

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
      <div className="flex items-center gap-3">
        <span className="w-[8.5rem] shrink-0 text-[0.78rem] font-semibold text-dim uppercase tracking-wide">{label}</span>
        <Progress value={(score / 10) * 100} className="h-[0.4rem] flex-1 bg-border [&>div]:bg-brand" />
        <span className="w-[2.6rem] shrink-0 text-right text-[0.82rem] font-bold text-foreground tabular-nums">{score.toFixed(1)}/10</span>
      </div>
      <p className="mt-0.5 ml-[9.25rem] text-[0.8rem] text-dim">{detail}</p>
    </div>
  )
}

export default function DifficultyPage() {
  const [source, setSource] = useState({ file: null })
  const { loading, error, result, run } = useAsyncAction()
  const loadingMessage = useRotatingMessage(LOADING_MESSAGES, 3200, loading)
  const progress = useSimulatedProgress(loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => difficulty(source))
  }

  return (
    <section className="animate-fade-in">
      <h2 className="text-2xl">Difficulty</h2>
      <p className="mb-7 max-w-[60ch] leading-relaxed text-dim">
        Score (MusicXML/MIDI) or audio &rarr; an estimated performance difficulty per part, with
        the exact numbers behind the rating -- fastest note value, pitch range, average melodic
        leap, chord density, key signature, and notes-per-second at the marked tempo. A
        deterministic, rule-based heuristic, not a certified grade level.
      </p>
      <form onSubmit={handleSubmit} className="flex max-w-[480px] flex-col gap-[1.15rem]">
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <Button type="submit" disabled={loading || !hasSource} size="lg"
          className="h-auto self-start rounded-(--radius-s) px-5 py-2.5 text-[0.95rem] font-bold shadow-(--shadow-s) hover:-translate-y-px hover:shadow-(--shadow-m)">
          {loading && <Spinner />}
          {loading ? 'Analyzing…' : 'Rate difficulty'}
        </Button>
        {loading && <LoadingProgress message={loadingMessage} progress={progress} />}
      </form>

      {error && <p className="mt-5 rounded-(--radius-s) border-l-[3px] border-error bg-error-wash px-4.5 py-3.5 text-[0.9rem] whitespace-pre-wrap text-error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="🎚️" text="Upload a score or audio file (or paste a YouTube link) to estimate how hard it is to play." />
      )}

      {result && (
        <div className="mt-8 border-t border-border pt-7">
          {result.accuracy_note && <p className="mb-5 border-l-[3px] border-border-strong pl-3 text-[0.85rem] text-dim italic">{result.accuracy_note}</p>}

          <div className="mb-6 flex flex-wrap items-baseline gap-4">
            <div className="text-5xl leading-none font-bold text-heading">
              {result.overall_score.toFixed(1)}
              <small className="text-[1.1rem] font-semibold text-dim">/10</small>
            </div>
            <Badge className="rounded-full bg-brand-wash px-3.5 py-1.5 text-[0.95rem] font-bold text-brand">{result.overall_level}</Badge>
          </div>

          <p className="mb-6 rounded-(--radius-m) border border-border bg-surface px-5.5 py-4.5 leading-relaxed">{result.summary}</p>

          <div className="flex flex-col gap-5">
            {result.per_part.map((part) => (
              <div className="rounded-(--radius-m) border border-border bg-surface px-5.5 py-[1.1rem] pb-[1.35rem]" key={part.name}>
                <div className="mb-3.5 flex items-center justify-between gap-3">
                  <h4 className="m-0 text-base">{part.name}</h4>
                  <span className="text-[0.9rem] font-bold text-brand">{part.level} &middot; {part.score.toFixed(1)}/10</span>
                </div>
                <div className="flex flex-col gap-3">
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
