import { useRef, useState } from 'react'
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
      className={dragOver ? 'file-drop drag-over' : 'file-drop'}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
    >
      <UploadIcon className="file-drop-icon" />
      <div className="file-drop-text">
        {file ? (
          <span className="file-drop-filename">{file.name}</span>
        ) : (
          <>
            <strong>{label}</strong>
            <span className="file-drop-hint">click to browse, or drag a file here</span>
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
