import { useState, useCallback } from 'react'

/** Shared loading/result/error state for the four pages' "submit and wait
 * for the API" flow -- identical pattern needed in all of them, so it's
 * factored out here instead of repeated four times. */
export function useAsyncAction() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const run = useCallback(async (fn) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await fn()
      setResult(data)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, result, run }
}
