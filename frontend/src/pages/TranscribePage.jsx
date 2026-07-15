import { useState } from 'react'
import { transcribe } from '../api'
import { downloadFile } from '../downloadFile'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import { useSimulatedProgress } from '../hooks/useSimulatedProgress'
import SheetMusic from '../components/SheetMusic'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import LoadingProgress from '../components/LoadingProgress'
import { DownloadIcon, Spinner } from '../components/Icons'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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
  const progress = useSimulatedProgress(loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => transcribe(source, { quantize, title }))
  }

  return (
    <section className="animate-fade-in">
      <h2 className="text-2xl">Transcribe</h2>
      <p className="mb-7 max-w-[60ch] leading-relaxed text-dim">
        Audio &rarr; notated score. Best-effort ML transcription -- see the accuracy note
        in the result below.
      </p>
      <form onSubmit={handleSubmit} className="flex max-w-[480px] flex-col gap-[1.15rem]">
        <AudioSourceInput source={source} onChange={setSource} accept="audio/*" label="Drop an audio file" />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="quantize" className="text-[0.82rem] font-semibold text-dim uppercase tracking-wide">
            Quantize (beat-grid subdivisions, e.g. 4 = 16th notes)
          </Label>
          <Input id="quantize" type="number" min="1" value={quantize} onChange={(e) => setQuantize(e.target.value)}
            className="h-auto rounded-(--radius-s) border-border-strong px-3 py-2.5 focus-visible:border-brand focus-visible:ring-brand-wash" />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="title" className="text-[0.82rem] font-semibold text-dim uppercase tracking-wide">
            Title (optional)
          </Label>
          <Input id="title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="defaults to filename"
            className="h-auto rounded-(--radius-s) border-border-strong px-3 py-2.5 focus-visible:border-brand focus-visible:ring-brand-wash" />
        </div>
        <Button type="submit" disabled={loading || !hasSource} size="lg"
          className="h-auto self-start rounded-(--radius-s) px-5 py-2.5 text-[0.95rem] font-bold shadow-(--shadow-s) hover:-translate-y-px hover:shadow-(--shadow-m)">
          {loading && <Spinner />}
          {loading ? 'Transcribing…' : 'Transcribe'}
        </Button>
        {loading && <LoadingProgress message={loadingMessage} progress={progress} />}
      </form>

      {error && <p className="mt-5 rounded-(--radius-s) border-l-[3px] border-error bg-error-wash px-4.5 py-3.5 text-[0.9rem] whitespace-pre-wrap text-error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="🎼" text="Upload a recording (or paste a YouTube link) to see it turned into notated sheet music." />
      )}

      {result && (
        <div className="mt-8 border-t border-border pt-7">
          <ul className="mb-4 flex flex-wrap gap-2 p-0">
            <li><Badge variant="outline" className="rounded-full border-border bg-surface px-3.5 py-1.5 text-[0.82rem] font-semibold text-foreground">Polyphony {result.polyphony?.toFixed(2)}</Badge></li>
            <li><Badge variant="outline" className="rounded-full border-border bg-surface px-3.5 py-1.5 text-[0.82rem] font-semibold text-foreground">{result.tempo_bpm?.toFixed(1)} BPM</Badge></li>
            <li><Badge variant="outline" className="rounded-full border-border bg-surface px-3.5 py-1.5 text-[0.82rem] font-semibold text-foreground">onset {result.thresholds_used?.onset_threshold} / frame {result.thresholds_used?.frame_threshold}</Badge></li>
          </ul>
          <p className="mb-5 border-l-[3px] border-border-strong pl-3 text-[0.85rem] text-dim italic">{result.accuracy_note}</p>
          <div className="mt-1 mb-5 flex flex-wrap gap-2.5">
            <Button
              type="button"
              variant="outline"
              className="h-auto gap-1.5 rounded-(--radius-s) border-border-strong px-4 py-2 text-[0.85rem] font-semibold hover:border-brand hover:text-brand"
              onClick={() => downloadFile(`${title || 'transcription'}.musicxml`, result.musicxml, 'application/vnd.recordare.musicxml+xml')}
            >
              <DownloadIcon className="size-4" /> Download MusicXML
            </Button>
          </div>
          <SheetMusic pages={result.sheet_music_svg} />
        </div>
      )}
    </section>
  )
}
