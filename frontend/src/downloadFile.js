/** Triggers a browser "Save As" for in-memory text content -- no server
 * round-trip needed since every downloadable artifact here (MusicXML,
 * .brl, .brf) already arrived in the API response body. */
export function downloadFile(filename, content, mimeType = 'text/plain') {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
