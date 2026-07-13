import { useState } from 'react'
import FileDrop from './FileDrop'

/** Toggle between "upload a file" and "paste a YouTube URL" -- the two
 * input modes every endpoint accepts. Exposes a single `source` object
 * ({ file } or { youtubeUrl }) via onChange, matching api.js's appendSource. */
export default function AudioSourceInput({ source, onChange, accept, label }) {
  const [mode, setMode] = useState('file')

  const setMode_ = (next) => {
    setMode(next)
    onChange(next === 'file' ? { file: source.file } : { youtubeUrl: source.youtubeUrl })
  }

  return (
    <div className="audio-source">
      <div className="source-toggle" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'file'}
          className={mode === 'file' ? 'source-toggle-btn active' : 'source-toggle-btn'}
          onClick={() => setMode_('file')}
        >
          Upload file
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'youtube'}
          className={mode === 'youtube' ? 'source-toggle-btn active' : 'source-toggle-btn'}
          onClick={() => setMode_('youtube')}
        >
          YouTube URL
        </button>
      </div>

      {mode === 'file' ? (
        <FileDrop
          file={source.file}
          onChange={(file) => onChange({ file })}
          accept={accept}
          label={label}
        />
      ) : (
        <input
          type="url"
          className="youtube-url-input"
          placeholder="https://www.youtube.com/watch?v=…"
          value={source.youtubeUrl || ''}
          onChange={(e) => onChange({ youtubeUrl: e.target.value })}
        />
      )}
    </div>
  )
}
