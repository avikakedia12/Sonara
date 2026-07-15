import { useState } from 'react'
import { braille } from '../api'
import { downloadFile } from '../downloadFile'
import { useAsyncAction } from '../hooks/useAsyncAction'
import { useRotatingMessage } from '../hooks/useRotatingMessage'
import { useSimulatedProgress } from '../hooks/useSimulatedProgress'
import AudioSourceInput from '../components/AudioSourceInput'
import EmptyState from '../components/EmptyState'
import LoadingProgress from '../components/LoadingProgress'
import { DownloadIcon, Spinner } from '../components/Icons'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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
  const progress = useSimulatedProgress(loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)
  const isAudio = Boolean(source.youtubeUrl) || (source.file && /\.(wav|mp3|flac|ogg|m4a|aiff?|aif)$/i.test(source.file.name))

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => braille(source, { partIndex, melodyOnly, quantize }))
  }

  return (
    <section className="animate-fade-in">
      <h2 className="text-2xl">Braille</h2>
      <p className="mb-7 max-w-[60ch] leading-relaxed text-dim">
        Score (MusicXML/MIDI) or audio &rarr; Braille Music Code. For dense/audio-transcribed
        input, "melody only" collapses chords to a single top-note line, which the Braille
        engine handles far better than raw polyphony.
      </p>
      <form onSubmit={handleSubmit} className="flex max-w-[480px] flex-col gap-[1.15rem]">
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="partIndex" className="text-[0.82rem] font-semibold text-dim uppercase tracking-wide">
            Part index
          </Label>
          <Input id="partIndex" type="number" min="0" value={partIndex} onChange={(e) => setPartIndex(e.target.value)}
            className="h-auto rounded-(--radius-s) border-border-strong px-3 py-2.5 focus-visible:border-brand focus-visible:ring-brand-wash" />
        </div>
        <div className="flex items-center gap-2.5">
          <Checkbox id="melodyOnly" checked={melodyOnly} onCheckedChange={(v) => setMelodyOnly(Boolean(v))}
            className="data-checked:border-brand data-checked:bg-brand" />
          <Label htmlFor="melodyOnly" className="text-[0.92rem] font-normal text-foreground normal-case">
            Melody only (recommended for dense/audio input)
          </Label>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="brailleQuantize" className="text-[0.82rem] font-semibold text-dim uppercase tracking-wide">
            Braille rhythm quantization (comma-separated divisors, e.g. "4,3" -- leave blank to skip)
          </Label>
          <Input id="brailleQuantize" type="text" value={quantize} onChange={(e) => setQuantize(e.target.value)} placeholder="e.g. 4,3"
            className="h-auto rounded-(--radius-s) border-border-strong px-3 py-2.5 focus-visible:border-brand focus-visible:ring-brand-wash" />
        </div>
        {isAudio && <p className="-mt-1.5 text-[0.82rem] text-dim">Audio input detected -- will be transcribed first (adaptive thresholds).</p>}
        <Button type="submit" disabled={loading || !hasSource} size="lg"
          className="h-auto self-start rounded-(--radius-s) px-5 py-2.5 text-[0.95rem] font-bold shadow-(--shadow-s) hover:-translate-y-px hover:shadow-(--shadow-m)">
          {loading && <Spinner />}
          {loading ? 'Converting…' : 'Convert to Braille'}
        </Button>
        {loading && <LoadingProgress message={loadingMessage} progress={progress} />}
      </form>

      {error && <p className="mt-5 rounded-(--radius-s) border-l-[3px] border-error bg-error-wash px-4.5 py-3.5 text-[0.9rem] whitespace-pre-wrap text-error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="⠿" text="Upload a score or audio file (or paste a YouTube link) to get Braille Music Code." />
      )}

      {result && (
        <div className="mt-8 border-t border-border pt-7">
          <ul className="mb-4 flex flex-wrap gap-2 p-0">
            <li><Badge variant="outline" className="rounded-full border-border bg-surface px-3.5 py-1.5 text-[0.82rem] font-semibold text-foreground">{result.chunks_transcribed} / {result.chunks_total} chunks transcribed</Badge></li>
          </ul>
          {result.accuracy_note && <p className="mb-5 border-l-[3px] border-border-strong pl-3 text-[0.85rem] text-dim italic">{result.accuracy_note}</p>}
          {result.failed_chunks?.length > 0 && (
            <p className="mb-5 rounded-(--radius-s) border-l-[3px] border-error bg-error-wash px-4.5 py-3.5 text-[0.9rem] text-error">Failed chunks (beats): {JSON.stringify(result.failed_chunks)}</p>
          )}
          <div className="mt-1 mb-5 flex flex-wrap gap-2.5">
            <Button type="button" variant="outline" className="h-auto gap-1.5 rounded-(--radius-s) border-border-strong px-4 py-2 text-[0.85rem] font-semibold hover:border-brand hover:text-brand" onClick={() => downloadFile('braille.brl', result.brl)}>
              <DownloadIcon className="size-4" /> Download .brl
            </Button>
            <Button type="button" variant="outline" className="h-auto gap-1.5 rounded-(--radius-s) border-border-strong px-4 py-2 text-[0.85rem] font-semibold hover:border-brand hover:text-brand" onClick={() => downloadFile('braille.brf', result.brf)}>
              <DownloadIcon className="size-4" /> Download .brf (embosser-ready)
            </Button>
          </div>
          <h3 className="text-lg">Braille (.brl)</h3>
          <pre className="overflow-x-auto rounded-(--radius-m) bg-heading p-6 text-[1.3rem] leading-[1.9] tracking-wide whitespace-pre text-[#f0edf7] shadow-(--shadow-s)">{result.brl}</pre>
        </div>
      )}
    </section>
  )
}
