import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'
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
    <div className="flex flex-col gap-2.5">
      <div className="inline-flex w-fit gap-0.5 self-start rounded-full border border-border bg-bg-canvas p-0.5" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'file'}
          className={cn(
            'rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-dim transition-colors',
            mode === 'file' && 'bg-surface text-brand shadow-(--shadow-s)'
          )}
          onClick={() => setMode_('file')}
        >
          Upload file
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'youtube'}
          className={cn(
            'rounded-full px-3.5 py-1.5 text-[0.8rem] font-semibold text-dim transition-colors',
            mode === 'youtube' && 'bg-surface text-brand shadow-(--shadow-s)'
          )}
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
        <Input
          type="url"
          className="h-auto rounded-(--radius-m) border-[1.5px] border-border-strong px-4 py-3.5 text-[0.95rem] focus-visible:border-brand focus-visible:ring-brand-wash"
          placeholder="https://www.youtube.com/watch?v=…"
          value={source.youtubeUrl || ''}
          onChange={(e) => onChange({ youtubeUrl: e.target.value })}
        />
      )}
    </div>
  )
}
