// VITE_API_BASE is set at build time on the deployed static site (see
// render.yaml); falls back to the local FastAPI dev server otherwise.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

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

/** Every endpoint accepts either a direct file upload or a youtube_url --
 * `source` is { file } or { youtubeUrl }, exactly one set. */
function appendSource(formData, fileFieldName, source) {
  if (source.youtubeUrl) {
    formData.append('youtube_url', source.youtubeUrl)
  } else if (source.file) {
    formData.append(fileFieldName, source.file)
  } else {
    throw new Error('Provide either a file or a YouTube URL.')
  }
}

export async function transcribe(source, { quantize, title, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  appendSource(fd, 'audio', source)
  appendIfSet(fd, 'quantize', quantize)
  appendIfSet(fd, 'title', title)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/transcribe', fd)
}

export async function braille(source, { partIndex, melodyOnly, quantize, chunkBeats, transcribeQuantize, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  appendSource(fd, 'score', source)
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

export async function transpose(source, targetInstrument, { partIndex, quantize, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  appendSource(fd, 'score', source)
  fd.append('target_instrument', targetInstrument)
  appendIfSet(fd, 'part_index', partIndex)
  appendIfSet(fd, 'quantize', quantize)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/transpose', fd)
}

export async function describe(source, { level, speak, transcribeQuantize, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  appendSource(fd, 'score', source)
  appendIfSet(fd, 'level', level)
  fd.append('speak', speak ? 'true' : 'false')
  appendIfSet(fd, 'transcribe_quantize', transcribeQuantize)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/describe', fd)
}

export async function difficulty(source, { transcribeQuantize, onsetThreshold, frameThreshold, minimumNoteLength } = {}) {
  const fd = new FormData()
  appendSource(fd, 'score', source)
  appendIfSet(fd, 'transcribe_quantize', transcribeQuantize)
  appendIfSet(fd, 'onset_threshold', onsetThreshold)
  appendIfSet(fd, 'frame_threshold', frameThreshold)
  appendIfSet(fd, 'minimum_note_length', minimumNoteLength)
  return postForm('/difficulty', fd)
}

export const INSTRUMENTS = [
  'flute', 'oboe', 'clarinet', 'bassoon', 'alto_sax', 'tenor_sax', 'trumpet',
  'horn', 'violin', 'viola', 'cello', 'contrabass', 'piano', 'english_horn',
]
