import { useEffect, useState } from 'react'

/** Eases a percentage toward (but never reaching) `cap` while `active` is
 * true, and resets to 0 once it isn't. There's no real progress to report --
 * every Sonara endpoint is a single blocking request -- so this only exists
 * to make the wait feel tracked, the same spirit as useRotatingMessage. */
export function useSimulatedProgress(active, { intervalMs = 200, cap = 96 } = {}) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!active) {
      setProgress(0)
      return
    }
    const id = setInterval(() => {
      setProgress((p) => p + (cap - p) * 0.06)
    }, intervalMs)
    return () => clearInterval(id)
  }, [active, intervalMs, cap])

  return Math.round(progress)
}
