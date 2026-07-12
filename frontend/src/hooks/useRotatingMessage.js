import { useEffect, useState } from 'react'

/** Cycles through `messages` every `intervalMs` while `active` is true --
 * used to keep the loading state feeling alive during the genuinely long
 * waits this pipeline sometimes has (real audio transcription can take
 * 20s-several minutes), instead of one static "Loading..." the whole time. */
export function useRotatingMessage(messages, intervalMs, active) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (!active) {
      setIndex(0)
      return
    }
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % messages.length)
    }, intervalMs)
    return () => clearInterval(id)
  }, [active, messages, intervalMs])

  return messages[index]
}
