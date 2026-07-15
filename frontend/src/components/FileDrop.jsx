import { useRef, useState } from 'react'
import { cn } from '@/lib/utils'
import { UploadIcon } from './Icons'

/** A styled file input that also accepts drag-and-drop, instead of the
 * browser's bare, inconsistently-styled <input type="file">. Same
 * underlying <input> for accessibility/keyboard support -- just visually
 * replaced with a clickable/droppable zone. */
export default function FileDrop({ file, onChange, accept, label }) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) onChange(dropped)
  }

  return (
    <div
      className={cn(
        'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-(--radius-m) border-[1.5px] border-dashed border-border-strong bg-surface px-4 py-7 text-center transition-colors',
        dragOver ? 'border-brand bg-brand-wash' : 'hover:border-brand hover:bg-brand-wash focus-visible:border-brand focus-visible:bg-brand-wash focus-visible:outline-none'
      )}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
    >
      <UploadIcon className="size-[1.6rem] text-dim" />
      <div className="flex flex-col gap-0.5 text-[0.9rem] font-medium text-foreground normal-case tracking-normal">
        {file ? (
          <span className="font-semibold text-heading break-all">{file.name}</span>
        ) : (
          <>
            <strong>{label}</strong>
            <span className="text-[0.8rem] font-normal text-dim">click to browse, or drag a file here</span>
          </>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={(e) => onChange(e.target.files[0])}
        hidden
      />
    </div>
  )
}
