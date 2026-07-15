import { useEffect, useRef, useState } from 'react'
import { usePianoTone } from '../hooks/usePianoTone'
import { SoundWaveIcon } from './Icons'

// A chromatic run (C4-F5), rendered as uniform keys -- no separate white/
// black key shapes. Each key gets a gradient "fill" at the bottom instead,
// so the whole row reads like a continuous ribbon/equalizer rather than a
// traditional keyboard. This also sidesteps the black-key-overlap bugs a
// two-shape layout kept running into (see git history) -- one shape, one
// simple flex row, nothing to misalign.
const KEYS = [
  { note: 'C4', label: 'C4', freq: 261.63 },
  { note: 'C#4', label: 'C♯4', freq: 277.18 },
  { note: 'D4', label: 'D4', freq: 293.66 },
  { note: 'D#4', label: 'D♯4', freq: 311.13 },
  { note: 'E4', label: 'E4', freq: 329.63 },
  { note: 'F4', label: 'F4', freq: 349.23 },
  { note: 'F#4', label: 'F♯4', freq: 369.99 },
  { note: 'G4', label: 'G4', freq: 392.0 },
  { note: 'G#4', label: 'G♯4', freq: 415.3 },
  { note: 'A4', label: 'A4', freq: 440.0 },
  { note: 'A#4', label: 'A♯4', freq: 466.16 },
  { note: 'B4', label: 'B4', freq: 493.88 },
  { note: 'C5', label: 'C5', freq: 523.25 },
  { note: 'C#5', label: 'C♯5', freq: 554.37 },
  { note: 'D5', label: 'D5', freq: 587.33 },
  { note: 'D#5', label: 'D♯5', freq: 622.25 },
  { note: 'E5', label: 'E5', freq: 659.25 },
  { note: 'F5', label: 'F5', freq: 698.46 },
]

const NOTE_BY_ID = Object.fromEntries(KEYS.map((k) => [k.note, k]))
const MAX_PREVIEW_NOTES = 5
const REPLAY_GAP_MS = 420

// Blends two sine waves at different frequencies/phases so the row curves
// like a real S-shaped ribbon (roughly 1.5 "humps") rather than a single
// symmetric arc. Rotation tracks the wave's own slope (its derivative),
// so keys visually align with the curve instead of tilting independently
// of it. Both amplitudes are modest on purpose -- getBoundingClientRect()
// on a rotated element returns its axis-aligned bounding box, not its true
// footprint, so a click aimed at that box's center can miss the key (or
// land on a neighbor) once the angle gets large; verified by driving every
// key with real click events.
function waveTransform(t) {
  const angle = t * Math.PI * 2.6
  const lift = -(Math.sin(angle) * 0.7 + Math.sin(angle * 0.5 + 1.1) * 0.3) * 62
  const rotate = (Math.cos(angle) * 0.7 + Math.cos(angle * 0.5 + 1.1) * 0.15) * 9
  return `rotate(${rotate.toFixed(1)}deg) translateY(${lift.toFixed(1)}px)`
}

// Height of each key's gradient "fill", as a fraction of the key's own
// height -- a different sine frequency/phase than the position wave so the
// fill heights read as organic variation (like an equalizer) rather than
// simply tracking how high each key sits.
function fillFraction(t) {
  const raw = 0.48 + Math.sin(t * Math.PI * 3.4 + 0.6) * 0.28
  return Math.min(0.82, Math.max(0.22, raw))
}

/** Decorative interactive piano banner shown above the tool tabs -- not a
 * tab itself, just something to scroll past on the way to the actual
 * pipeline. No visible copy by design; the piano keyboard's own
 * aria-label/per-key aria-labels are what a screen reader picks up, so it
 * stays discoverable without a paragraph of on-page text. */
export default function PianoHero() {
  const playNote = usePianoTone()
  const [playedNotes, setPlayedNotes] = useState([])
  const [isReplaying, setIsReplaying] = useState(false)
  const timeoutsRef = useRef([])

  useEffect(() => () => timeoutsRef.current.forEach(clearTimeout), [])

  const handlePlay = (key) => {
    playNote(key.freq)
    setPlayedNotes((prev) => [...prev, key.note].slice(-MAX_PREVIEW_NOTES))
  }

  const handleReplay = () => {
    timeoutsRef.current.forEach(clearTimeout)
    timeoutsRef.current = []
    setIsReplaying(true)
    playedNotes.forEach((noteId, i) => {
      timeoutsRef.current.push(setTimeout(() => playNote(NOTE_BY_ID[noteId].freq), i * REPLAY_GAP_MS))
    })
    timeoutsRef.current.push(setTimeout(() => setIsReplaying(false), playedNotes.length * REPLAY_GAP_MS))
  }

  const handleClear = () => setPlayedNotes([])

  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div
        className="relative mx-auto flex h-[62%] w-full max-w-[1600px] items-end gap-[3px] px-[5vw] pt-5 pb-[45px]"
        role="group"
        aria-label="Interactive piano keyboard -- play a few notes"
      >
        {KEYS.map((key, i) => {
          const t = i / (KEYS.length - 1)
          return (
            <button
              key={key.note}
              type="button"
              className="relative h-[min(320px,34vh)] min-w-0 flex-1 origin-bottom cursor-pointer overflow-hidden rounded-lg bg-surface p-0 shadow-(--shadow-s) transition-[filter] duration-150 ease-out hover:brightness-[1.06] focus:brightness-[1.06] focus:outline-[3px] focus:outline-offset-2 focus:outline-brand"
              style={{ transform: waveTransform(t) }}
              aria-label={`Play ${key.note.replace('#', ' sharp ')}`}
              onClick={() => handlePlay(key)}
            >
              <span
                className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-b from-[#6d28d9] to-[#f97316] dark:from-[#a78bfa] dark:to-[#fb923c]"
                style={{ height: `${(fillFraction(t) * 100).toFixed(0)}%` }}
                aria-hidden="true"
              />
            </button>
          )
        })}
      </div>

      <div
        className="empty:hidden absolute bottom-8 left-1/2 z-2 max-w-[min(480px,90vw)] -translate-x-1/2 rounded-(--radius-m) border border-border bg-surface px-6 py-4 text-center shadow-(--shadow-m)"
        aria-live="polite"
      >
        {playedNotes.length > 0 && playedNotes.length < MAX_PREVIEW_NOTES && (
          <>
            <p className="m-0 mb-2 text-[0.82rem] font-semibold text-dim uppercase tracking-wide">You played:</p>
            <ol className="m-0 mb-4 flex list-none flex-wrap justify-center gap-2 p-0">
              {playedNotes.map((noteId, i) => (
                <li key={i} className="rounded-full bg-brand-wash px-3.5 py-1.5 text-[0.9rem] font-bold text-brand">{NOTE_BY_ID[noteId].label}</li>
              ))}
            </ol>
            <div className="flex justify-center gap-2.5">
              <button
                type="button"
                onClick={handleReplay}
                disabled={isReplaying}
                className="rounded-(--radius-s) border border-brand bg-surface px-[1.1rem] py-2 text-[0.85rem] font-semibold text-brand transition-colors disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isReplaying ? 'Replaying…' : 'Replay'}
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="rounded-(--radius-s) border border-border-strong bg-surface px-[1.1rem] py-2 text-[0.85rem] font-semibold text-foreground transition-colors hover:border-brand hover:text-brand"
              >
                Clear
              </button>
            </div>
          </>
        )}

        {playedNotes.length === MAX_PREVIEW_NOTES && (
          <div className="animate-fade-in">
            <p className="m-0 mb-4 text-[1.05rem] leading-relaxed font-semibold text-heading">
              You could see the keys and play them.
              <br />
              A blind musician can't — that's exactly why Sonara exists.
            </p>
            <div className="inline-flex items-center gap-2">
              <SoundWaveIcon className="size-[1.8rem] shrink-0 text-[#8b5cf6]" aria-hidden="true" />
              <span className="bg-gradient-to-r from-[#7c3aed] to-[#f97316] bg-clip-text text-[2rem] font-extrabold tracking-tight text-transparent">sonara</span>
            </div>
            <p className="mt-1 mb-0 text-[0.85rem] tracking-wide text-dim">hear it . see it . feel it .</p>
            <button
              type="button"
              onClick={handleClear}
              className="mx-auto mt-4 block cursor-pointer border-none bg-transparent text-[0.8rem] font-semibold text-dim underline underline-offset-2 hover:text-brand"
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {playedNotes.length === 0 && (
        <div
          className="absolute bottom-6 left-1/2 z-2 flex -translate-x-1/2 animate-bob flex-col items-center gap-0.5 text-xs font-semibold tracking-wider text-dim uppercase"
          aria-hidden="true"
        >
          <span>Scroll for the tools</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-[1.1rem]">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      )}
    </div>
  )
}
