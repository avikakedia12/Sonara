import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { usePianoTone } from '../hooks/usePianoTone'
import { SoundWaveIcon } from './Icons'

// Almost two octaves (C4-F5) -- enough keys that the wave reads as a full,
// rich keyboard across the whole width of a wide screen rather than a
// sparse handful of stretched-out keys.
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
]

// afterIndex = the white key it's visually anchored between (straddling
// the gap after that white key's slot) -- matches real piano layout, which
// skips a black key between E/F and B/C.
const BLACK_KEYS = [
  { note: 'C#4', label: 'C♯4', freq: 277.18, afterIndex: 0 },
  { note: 'D#4', label: 'D♯4', freq: 311.13, afterIndex: 1 },
  { note: 'F#4', label: 'F♯4', freq: 369.99, afterIndex: 3 },
  { note: 'G#4', label: 'G♯4', freq: 415.3, afterIndex: 4 },
  { note: 'A#4', label: 'A♯4', freq: 466.16, afterIndex: 5 },
  { note: 'C#5', label: 'C♯5', freq: 554.37, afterIndex: 7 },
  { note: 'D#5', label: 'D♯5', freq: 622.25, afterIndex: 8 },
]

const ALL_KEYS = [...WHITE_KEYS, ...BLACK_KEYS]
const NOTE_BY_ID = Object.fromEntries(ALL_KEYS.map((k) => [k.note, k]))
const MAX_PREVIEW_NOTES = 5
const REPLAY_GAP_MS = 420

// Individually rotates and lifts each key along a gentle arc so the row
// reads as a "wave" rather than a flat keyboard -- purely decorative, t is
// each key's position from 0 (left) to 1 (right).
function waveTransform(t) {
  // Rotation is deliberately modest: getBoundingClientRect() on a rotated
  // element returns its axis-aligned bounding box, not its actual rotated
  // footprint -- a click aimed at that box's center can land outside the
  // key entirely (or on a neighboring key) once the angle gets large
  // enough, verified by driving this with real click events.
  const rotate = -6 + t * 24
  const lift = -Math.sin(t * Math.PI * 0.9) * 65
  return `rotate(${rotate.toFixed(1)}deg) translateY(${lift.toFixed(1)}px)`
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
  const whiteKeyRefs = useRef([])
  // Pixel offsets (relative to .piano's left edge) for each black key,
  // measured from the actual rendered white keys rather than computed via a
  // hand-derived percentage formula -- a percentage-of-container approach
  // doesn't account for .piano's own padding or the flex gaps between white
  // keys, which put every black key visibly off from the boundary it's
  // supposed to straddle (confirmed by screenshotting the result: the first
  // black key covered nearly the entire first white key). offsetLeft/
  // offsetWidth reflect the pre-transform layout box, so they're also
  // unaffected by each key's own rotate/translateY.
  const [blackKeyLefts, setBlackKeyLefts] = useState(() => BLACK_KEYS.map(() => 0))

  useLayoutEffect(() => {
    const measure = () => {
      setBlackKeyLefts(
        BLACK_KEYS.map((key) => {
          const before = whiteKeyRefs.current[key.afterIndex]
          const after = whiteKeyRefs.current[key.afterIndex + 1]
          if (!before || !after) return 0
          const boundary = before.offsetLeft + before.offsetWidth
          const gapMidpoint = (boundary + after.offsetLeft) / 2
          return gapMidpoint
        })
      )
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])

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
    <div className="piano-hero">
      <div className="piano" role="group" aria-label="Interactive piano keyboard -- play a few notes">
        {WHITE_KEYS.map((key, i) => {
          const t = i / (WHITE_KEYS.length - 1)
          return (
            <button
              key={key.note}
              ref={(el) => { whiteKeyRefs.current[i] = el }}
              type="button"
              className="piano-key piano-key-white"
              style={{ transform: waveTransform(t) }}
              aria-label={`Play ${key.label}`}
              onClick={() => handlePlay(key)}
            />
          )
        })}
        {BLACK_KEYS.map((key, i) => {
          const t = (key.afterIndex + 0.5) / (WHITE_KEYS.length - 1)
          return (
            <button
              key={key.note}
              type="button"
              className="piano-key piano-key-black"
              style={{ left: `${blackKeyLefts[i]}px`, transform: `translateX(-50%) ${waveTransform(t)}` }}
              aria-label={`Play ${key.note.replace('#', ' sharp ')}`}
              onClick={() => handlePlay(key)}
            />
          )
        })}
      </div>

      <div className="piano-preview" aria-live="polite">
        {playedNotes.length > 0 && playedNotes.length < MAX_PREVIEW_NOTES && (
          <>
            <p className="piano-preview-label">You played:</p>
            <ol className="piano-preview-notes">
              {playedNotes.map((noteId, i) => (
                <li key={i}>{NOTE_BY_ID[noteId].label}</li>
              ))}
            </ol>
            <div className="piano-preview-actions">
              <button type="button" onClick={handleReplay} disabled={isReplaying}>
                {isReplaying ? 'Replaying…' : 'Replay'}
              </button>
              <button type="button" onClick={handleClear}>
                Clear
              </button>
            </div>
          </>
        )}

        {playedNotes.length === MAX_PREVIEW_NOTES && (
          <div className="piano-reveal">
            <p className="piano-reveal-message">
              You could see the keys and play them.
              <br />
              A blind musician can't — that's exactly why Sonara exists.
            </p>
            <div className="piano-logo">
              <SoundWaveIcon className="piano-logo-icon" aria-hidden="true" />
              <span className="piano-logo-word">sonara</span>
            </div>
            <p className="piano-logo-tagline">hear it . see it . feel it .</p>
            <button type="button" className="piano-reveal-clear" onClick={handleClear}>
              Clear
            </button>
          </div>
        )}
      </div>

      {playedNotes.length === 0 && (
        <div className="hero-scroll-hint" aria-hidden="true">
          <span>Scroll for the tools</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      )}
    </div>
  )
}
