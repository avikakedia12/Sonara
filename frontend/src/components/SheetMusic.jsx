/** Renders an array of SVG page strings (as returned by /transcribe and
 * /transpose's sheet_music_svg field) directly as real notation, not JSON
 * text -- each page is injected as raw SVG markup via dangerouslySetInnerHTML,
 * which is safe here since the SVG comes from our own trusted API, not
 * user-supplied HTML. */
export default function SheetMusic({ pages }) {
  if (!pages || pages.length === 0) return null

  return (
    <div className="sheet-music">
      {pages.map((svg, i) => (
        // eslint-disable-next-line react/no-danger
        <div key={i} className="sheet-music-page" dangerouslySetInnerHTML={{ __html: svg }} />
      ))}
    </div>
  )
}
