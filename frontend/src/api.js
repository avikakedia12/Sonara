const API_BASE = 'http://127.0.0.1:8000'

/** POST a FormData body to `path` and return the parsed JSON response.
 * Throws an Error with the server's `detail` message on a non-2xx response,
 * since every Sonara endpoint returns { detail: "..." } on failure. */
async function postForm(path, formData) {
  const resp = await fetch(`${API_BASE}${path}`, { method: 'POST', body: formData })
  const data = await resp.json().catch(() => null)
  if (!resp.ok) {
    const detail = data && data.detail ? data.detail : `${resp.status} ${resp.statusText}`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return data
}

/** Appends only the params that have a real value -- Optional[...] Form
 * fields on the backend should be omitted, not sent as "" or 0, to use
 * their tuned defaults (adaptive thresholds, 40ms note-length floor, etc.)
 * instead of accidentally overriding them. */
function appendIfSet(formData, key, value) {
  if (value !== '' && value !== null && value !== undefined) {
    formData.append(key, value)
  }
}

export async function transcribe(file, { quantize, title, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  fd.append('audio', file)
  appendIfSet(fd, 'quantize', quantize)
  appendIfSet(fd, 'title', title)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/transcribe', fd)
}

export async function braille(file, { partIndex, melodyOnly, quantize, chunkBeats, transcribeQuantize, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  fd.append('score', file)
  appendIfSet(fd, 'part_index', partIndex)
  fd.append('melody_only', melodyOnly ? 'true' : 'false')
  appendIfSet(fd, 'quantize', quantize)
  appendIfSet(fd, 'chunk_beats', chunkBeats)
  appendIfSet(fd, 'transcribe_quantize', transcribeQuantize)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/braille', fd)
}

export async function transpose(file, targetInstrument, { partIndex, quantize, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  fd.append('score', file)
  fd.append('target_instrument', targetInstrument)
  appendIfSet(fd, 'part_index', partIndex)
  appendIfSet(fd, 'quantize', quantize)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/transpose', fd)
}

export async function describe(file, { level, speak, transcribeQuantize, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  fd.append('score', file)
  appendIfSet(fd, 'level', level)
  fd.append('speak', speak ? 'true' : 'false')
  appendIfSet(fd, 'transcribe_quantize', transcribeQuantize)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/describe', fd)
}

export const INSTRUMENTS = [
  'flute', 'oboe', 'clarinet', 'bassoon', 'alto_sax', 'tenor_sax', 'trumpet',
  'horn', 'violin', 'viola', 'cello', 'contrabass', 'piano', 'english_horn',
]
