/** Small inline SVG icons -- no icon-library dependency for a handful of
 * glyphs. currentColor throughout so they inherit whatever text color the
 * surrounding button/heading is using. */

export function TranscribeIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </svg>
  )
}

export function BrailleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...props}>
      <circle cx="7" cy="6" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="14" cy="6" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="7" cy="12" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="14" cy="12" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="7" cy="18" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="14" cy="18" r="1.6" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function TransposeIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 8h13M17 8l-3-3M17 8l-3 3" />
      <path d="M20 16H7M7 16l3-3M7 16l3 3" />
    </svg>
  )
}

export function DescribeIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 4h16v12H8l-4 4V4z" />
      <path d="M8 9h8M8 12h5" />
    </svg>
  )
}

export function UploadIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 16V4M12 4l-4 4M12 4l4 4" />
      <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
    </svg>
  )
}

export function Spinner(props) {
  return (
    <svg className="spinner" viewBox="0 0 24 24" fill="none" {...props}>
      <circle cx="12" cy="12" r="9.5" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21.5 12a9.5 9.5 0 0 0-9.5-9.5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
