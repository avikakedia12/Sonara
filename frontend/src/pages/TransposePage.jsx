import { useState } from 'react'
import { transpose, INSTRUMENTS } from '../api'
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
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion'

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
  const progress = useSimulatedProgress(loading)

  const hasSource = Boolean(source.file || source.youtubeUrl)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!hasSource) return
    run(() => transpose(source, targetInstrument))
  }

  return (
    <section className="animate-fade-in">
      <h2 className="text-2xl">Transpose</h2>
      <p className="mb-7 max-w-[60ch] leading-relaxed text-dim">
        Score (MusicXML/MIDI) or audio + a target instrument &rarr; a transposed score written
        for that instrument, range-checked against it. Out-of-range notes are flagged, never
        silently altered -- that's a judgment call for a human.
      </p>
      <form onSubmit={handleSubmit} className="flex max-w-[480px] flex-col gap-[1.15rem]">
        <AudioSourceInput source={source} onChange={setSource} label="Drop a score or audio file" />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="targetInstrument" className="text-[0.82rem] font-semibold text-dim uppercase tracking-wide">
            Target instrument
          </Label>
          <Select value={targetInstrument} onValueChange={setTargetInstrument}>
            <SelectTrigger id="targetInstrument" className="h-auto w-full rounded-(--radius-s) border-border-strong px-3 py-2.5 focus-visible:border-brand focus-visible:ring-brand-wash">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {INSTRUMENTS.map((name) => (
                <SelectItem key={name} value={name}>{name.replace('_', ' ')}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button type="submit" disabled={loading || !hasSource} size="lg"
          className="h-auto self-start rounded-(--radius-s) px-5 py-2.5 text-[0.95rem] font-bold shadow-(--shadow-s) hover:-translate-y-px hover:shadow-(--shadow-m)">
          {loading && <Spinner />}
          {loading ? 'Transposing…' : 'Transpose'}
        </Button>
        {loading && <LoadingProgress message={loadingMessage} progress={progress} />}
      </form>

      {error && <p className="mt-5 rounded-(--radius-s) border-l-[3px] border-error bg-error-wash px-4.5 py-3.5 text-[0.9rem] whitespace-pre-wrap text-error">Error: {error}</p>}

      {!error && !result && !loading && (
        <EmptyState icon="🎻" text="Upload a score or audio file (or paste a YouTube link) and pick a target instrument." />
      )}

      {result && (
        <div className="mt-8 border-t border-border pt-7">
          <ul className="mb-4 flex flex-wrap gap-2 p-0">
            <li><Badge variant="outline" className="rounded-full border-border bg-surface px-3.5 py-1.5 text-[0.82rem] font-semibold text-foreground">Target: {result.target_instrument}</Badge></li>
            <li><Badge variant="outline" className="rounded-full border-border bg-surface px-3.5 py-1.5 text-[0.82rem] font-semibold text-foreground">Range {result.playable_range?.low}&ndash;{result.playable_range?.high}</Badge></li>
          </ul>
          {result.accuracy_note && <p className="mb-5 border-l-[3px] border-border-strong pl-3 text-[0.85rem] text-dim italic">{result.accuracy_note}</p>}
          {result.out_of_range_notes?.length > 0 && (
            <Accordion type="single" collapsible className="mb-5 rounded-(--radius-m) border border-border bg-surface px-4.5">
              <AccordionItem value="out-of-range" className="border-b-0">
                <AccordionTrigger className="text-[0.9rem] font-semibold hover:no-underline">
                  {result.out_of_range_notes.length} note(s) outside playable range (flagged, not altered)
                </AccordionTrigger>
                <AccordionContent>
                  <ul className="m-0 max-h-[220px] list-none overflow-y-auto pl-0 text-[0.87rem]">
                    {result.out_of_range_notes.map((n, i) => (
                      <li key={i} className="py-0.5 text-dim">beat {n.offset.toFixed(2)}: {n.pitch} ({n.direction} range)</li>
                    ))}
                  </ul>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          )}
          <div className="mt-1 mb-5 flex flex-wrap gap-2.5">
            <Button
              type="button"
              variant="outline"
              className="h-auto gap-1.5 rounded-(--radius-s) border-border-strong px-4 py-2 text-[0.85rem] font-semibold hover:border-brand hover:text-brand"
              onClick={() => downloadFile(`transposed_${result.target_instrument}.musicxml`, result.musicxml, 'application/vnd.recordare.musicxml+xml')}
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
