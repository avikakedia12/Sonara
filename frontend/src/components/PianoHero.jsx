import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { usePianoTone } from '../hooks/usePianoTone'
import { SoundWaveIcon } from './Icons'

// Two octaves, C4-B5, laid out as a real keyboard: white keys in a flat row
// spanning the full width, black keys positioned over the boundaries between
// them (skipping E-F and B-C, which have no sharp/flat in between).
const WHITE_KEYS = [
  { note: 'C4', label: 'C4', freq: 261.63 },
  { note: 'D4', label: 'D4', freq: 293.66 },
  { note: 'E4', label: 'E4', freq: 329.63 },
  { note: 'F4', label: 'F4', freq: 349.23 },
  { note: 'G4', label: 'G4', freq: 392.0 },
  { note: 'A4', label: 'A4', freq: 440.0 },
  { note: 'B4', label: 'B4', freq: 493.88 },
  { note: 'C5', label: 'C5', freq: 523.25 },
  { note: 'D5', label: 'D5', freq: 587.33 },
  { note: 'E5', label: 'E5', freq: 659.25 },
  { note: 'F5', label: 'F5', freq: 698.46 },
  { note: 'G5', label: 'G5', freq: 783.99 },
  { note: 'A5', label: 'A5', freq: 880.0 },
  { note: 'B5', label: 'B5', freq: 987.77 },
]

// afterWhiteIndex: this black key sits centered on the boundary right after
// WHITE_KEYS[afterWhiteIndex] -- e.g. 0 means the C#/Db between C and D.
const BLACK_KEYS = [
  { note: 'C#4', label: 'C♯4', freq: 277.18, afterWhiteIndex: 0 },
  { note: 'D#4', label: 'D♯4', freq: 311.13, afterWhiteIndex: 1 },
  { note: 'F#4', label: 'F♯4', freq: 369.99, afterWhiteIndex: 3 },
  { note: 'G#4', label: 'G♯4', freq: 415.3, afterWhiteIndex: 4 },
  { note: 'A#4', label: 'A♯4', freq: 466.16, afterWhiteIndex: 5 },
  { note: 'C#5', label: 'C♯5', freq: 554.37, afterWhiteIndex: 7 },
  { note: 'D#5', label: 'D♯5', freq: 622.25, afterWhiteIndex: 8 },
  { note: 'F#5', label: 'F♯5', freq: 739.99, afterWhiteIndex: 10 },
  { note: 'G#5', label: 'G♯5', freq: 830.61, afterWhiteIndex: 11 },
  { note: 'A#5', label: 'A♯5', freq: 932.33, afterWhiteIndex: 12 },
]

const NOTE_BY_ID = Object.fromEntries([...WHITE_KEYS, ...BLACK_KEYS].map((k) => [k.note, k]))
const MAX_PREVIEW_NOTES = 5
const REPLAY_GAP_MS = 420

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
  const containerRef = useRef(null)
  const whiteKeyRefs = useRef([])
  const [blackKeyOffsets, setBlackKeyOffsets] = useState([])

  useEffect(() => () => timeoutsRef.current.forEach(clearTimeout), [])

  // Black keys are positioned from the *measured* pixel edges of the white
  // keys they sit between (offsetLeft/offsetWidth), not a hand-derived
  // percentage formula -- a formula that didn't account for the row's own
  // padding is exactly what caused the first black key to smother the first
  // white key in an earlier version of this component (see git history).
  // Recomputed on resize since the white keys' widths are flex-driven.
  useLayoutEffect(() => {
    function measure() {
      const container = containerRef.current
      if (!container) return
      const offsets = BLACK_KEYS.map((key) => {
        const beforeEl = whiteKeyRefs.current[key.afterWhiteIndex]
        return beforeEl ? beforeEl.offsetLeft + beforeEl.offsetWidth : null
      })
      setBlackKeyOffsets(offsets)
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])

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
        ref={containerRef}
        className="relative mx-auto flex h-[62%] w-full max-w-[1600px] items-stretch"
        role="group"
        aria-label="Interactive piano keyboard -- play a few notes"
      >
        {WHITE_KEYS.map((key, i) => (
          <button
            key={key.note}
            ref={(el) => { whiteKeyRefs.current[i] = el }}
            type="button"
            className="relative z-0 h-full min-w-0 flex-1 cursor-pointer rounded-b-md border-x border-b border-black/10 bg-white shadow-(--shadow-s) transition-[filter] duration-150 ease-out first:rounded-l-lg first:border-l-0 last:rounded-r-lg last:border-r-0 hover:brightness-95 focus:z-20 focus:brightness-95 focus:outline-[3px] focus:-outline-offset-4 focus:outline-brand"
            aria-label={`Play ${key.note}`}
            onClick={() => handlePlay(key)}
          />
        ))}

        {BLACK_KEYS.map((key, i) => {
          const left = blackKeyOffsets[i]
          if (left == null) return null
          return (
            <button
              key={key.note}
              type="button"
              className="absolute top-0 z-10 h-[60%] w-[6.5%] max-w-9 -translate-x-1/2 cursor-pointer rounded-b-md bg-[#18161d] shadow-[0_3px_6px_rgba(0,0,0,0.45)] transition-[filter] duration-150 ease-out hover:brightness-125 focus:z-20 focus:brightness-125 focus:outline-[3px] focus:outline-offset-1 focus:outline-brand"
              style={{ left }}
              aria-label={`Play ${key.note.replace('#', ' sharp ')}`}
              onClick={() => handlePlay(key)}
            />
          )
        })}
      </div>

      <div
        className="empty:hidden absolute bottom-8 left-1/2 z-30 max-w-[min(480px,90vw)] -translate-x-1/2 rounded-(--radius-m) border border-border bg-surface px-6 py-4 text-center shadow-(--shadow-m)"
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
          className="absolute bottom-6 left-1/2 z-30 flex -translate-x-1/2 animate-bob flex-col items-center gap-0.5 text-xs font-semibold tracking-wider text-dim uppercase"
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
