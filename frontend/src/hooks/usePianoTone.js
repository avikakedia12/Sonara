import { useCallback, useEffect, useRef } from 'react'

/** Synthesizes a short piano-ish tone via the Web Audio API on demand -- no
 * audio assets to fetch, just an oscillator plus a quick attack/decay
 * envelope per note. The AudioContext is created lazily on first play
 * (browsers require a user gesture before audio can start) and reused
 * across notes rather than one-per-call. */
export function usePianoTone() {
  const ctxRef = useRef(null)

  useEffect(() => () => ctxRef.current?.close(), [])

  const playNote = useCallback((frequency) => {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    if (!AudioContextClass) return
    if (!ctxRef.current) ctxRef.current = new AudioContextClass()
    const ctx = ctxRef.current
    if (ctx.state === 'suspended') ctx.resume()

    const now = ctx.currentTime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.value = frequency
    // exponentialRampToValueAtTime can't ramp to/from 0, hence 0.0001 floor.
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.3, now + 0.015)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start(now)
    osc.stop(now + 0.65)
  }, [])

  return playNote
}
