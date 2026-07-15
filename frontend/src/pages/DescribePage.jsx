import { useState } from 'react'
import { describe } from '../api'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import { useSimulatedProgress } from '../hooks/useSimulatedProgress'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import LoadingProgress from '../components/LoadingProgress'
import { Spinner } from '../components/Icons'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

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
  const progress = useSimulatedProgress(loading)

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
    <section className="animate-fade-in">
      <h2 className="text-2xl">Describe</h2>
      <p className="mb-7 max-w-[60ch] leading-relaxed text-dim">
        Score (MusicXML/MIDI) or audio &rarr; a plain-text structural description (title, key,
        tempo, instrumentation, length) -- meant to orient a blind musician before reading the
        piece note-by-note. Optionally spoken aloud.
      </p>
      <form onSubmit={handleSubmit} className="flex max-w-[480px] flex-col gap-[1.15rem]">
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="level" className="text-[0.82rem] font-semibold text-dim uppercase tracking-wide">
            Detail level
          </Label>
          <Select value={level} onValueChange={setLevel}>
            <SelectTrigger id="level" className="h-auto w-full rounded-(--radius-s) border-border-strong px-3 py-2.5 focus-visible:border-brand focus-visible:ring-brand-wash">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="brief">Brief</SelectItem>
              <SelectItem value="standard">Standard</SelectItem>
              <SelectItem value="detailed">Detailed</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2.5">
          <Checkbox id="speak" checked={speak} onCheckedChange={(v) => setSpeak(Boolean(v))}
            className="data-checked:border-brand data-checked:bg-brand" />
          <Label htmlFor="speak" className="text-[0.92rem] font-normal text-foreground normal-case">
            Also render as speech (requires pyttsx3 installed server-side)
          </Label>
        </div>
        <Button type="submit" disabled={loading || !hasSource} size="lg"
          className="h-auto self-start rounded-(--radius-s) px-5 py-2.5 text-[0.95rem] font-bold shadow-(--shadow-s) hover:-translate-y-px hover:shadow-(--shadow-m)">
          {loading && <Spinner />}
          {loading ? 'Describing…' : 'Describe'}
        </Button>
        {loading && <LoadingProgress message={loadingMessage} progress={progress} />}
      </form>

      {error && <p className="mt-5 rounded-(--radius-s) border-l-[3px] border-error bg-error-wash px-4.5 py-3.5 text-[0.9rem] whitespace-pre-wrap text-error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="📝" text="Upload a score or audio file (or paste a YouTube link) to get a structural description." />
      )}

      {result && (
        <div className="mt-8 border-t border-border pt-7">
          {result.accuracy_note && <p className="mb-5 border-l-[3px] border-border-strong pl-3 text-[0.85rem] text-dim italic">{result.accuracy_note}</p>}
          <p className="rounded-(--radius-m) border border-border bg-surface px-5.5 py-4.5 leading-relaxed">{result.description}</p>
          {audioSrc && (
            <audio controls src={audioSrc} className="mt-5 w-full">
              Your browser doesn't support inline audio playback.
            </audio>
          )}
        </div>
      )}
    </section>
  )
}
