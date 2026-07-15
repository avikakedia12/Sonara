import Reveal from '../components/Reveal'
import PianoHero from '../components/PianoHero'
import {
  TranscribeIcon,
  BrailleIcon,
  TransposeIcon,
  DescribeIcon,
  DifficultyIcon,
  LayersIcon,
  PulseIcon,
  SoundWaveIcon,
} from '../components/Icons'

const APPROACH = [
  {
    Icon: LayersIcon,
    name: 'Demucs',
    blurb: 'Separates a mixed recording into isolated stems, so a single instrument can be transcribed on its own instead of fighting the rest of the ensemble.',
  },
  {
    Icon: SoundWaveIcon,
    name: 'Basic Pitch',
    blurb: "Spotify's pretrained polyphonic model turns raw audio into note events -- pitch, onset, and duration -- without needing a custom-trained model per instrument.",
  },
  {
    Icon: PulseIcon,
    name: 'CREPE / pYIN',
    blurb: 'Monophonic pitch trackers that sharpen single-line melodic material, catching pitch a polyphonic model can smear across nearby notes.',
  },
  {
    Icon: TranscribeIcon,
    name: 'music21',
    blurb: 'Quantizes raw note timings onto a musical beat grid, then handles notation, Braille transcription, transposition, and structural analysis downstream.',
  },
]

const FUNCTIONS = [
  { Icon: TranscribeIcon, name: 'Transcribe', blurb: 'Audio recording in, a notated score (MusicXML) out -- quantized onto real musical durations, not raw seconds.' },
  { Icon: BrailleIcon, name: 'Braille', blurb: 'Score to Braille Music Code, using music21’s built-in Braille transcriber -- output as both readable Unicode and embosser-ready BRF.' },
  { Icon: DescribeIcon, name: 'Describe', blurb: 'A plain-text structural summary -- key, tempo, instrumentation, length -- optionally read aloud via offline text-to-speech.' },
  { Icon: TransposeIcon, name: 'Transpose', blurb: 'Retarget a score to a different instrument’s written pitch, range-checked so out-of-range notes are flagged, never silently altered.' },
  { Icon: DifficultyIcon, name: 'Difficulty', blurb: 'A read on how demanding a piece is to play, so a musician or teacher can gauge fit before committing to it.' },
]

export default function LandingPage() {
  return (
    <div className="relative">
      <section className="relative flex min-h-svh flex-col items-center overflow-hidden">
        <div className="relative z-20 flex flex-col items-center pt-[9vh] text-center">
          <img src="/favicon.svg" alt="" aria-hidden="true" className="size-16 drop-shadow-[0_0_18px_rgba(134,59,255,0.55)]" />
          <h1 className="mt-4 mb-0 bg-gradient-to-r from-[#863bff] to-[#47bfff] bg-clip-text text-[3.2rem] leading-none font-extrabold tracking-tight text-transparent">
            sonara
          </h1>
          <p className="mt-3 mb-0 text-[0.95rem] font-semibold tracking-[0.15em] text-dim uppercase">
            hear it &middot; see it &middot; feel it
          </p>
          <p className="mt-5 max-w-[46ch] text-[1.05rem] leading-relaxed text-dim">
            Sonara turns a recording into sheet music, Braille music notation, and spoken
            narration -- so a blind or low-vision musician can read a piece straight from
            audio, not wait on a manual transcription.
          </p>
        </div>

        <div className="relative mt-auto h-[48vh] min-h-[280px] w-full">
          <PianoHero />
        </div>
      </section>

      <section id="research" className="relative mx-auto max-w-[880px] px-6 py-28">
        <Reveal>
          <p className="mb-2 text-[0.82rem] font-bold tracking-[0.2em] text-brand uppercase">Research</p>
          <h2 className="mb-5 text-[2rem]">Why Sonara exists</h2>
          <p className="max-w-[64ch] text-[1.02rem] leading-relaxed text-dim">
            Braille music notation opens a piece up to a blind or low-vision musician the same
            way print notation does for a sighted one -- but getting a recording transcribed
            into it usually means finding one of the small number of trained music Braille
            transcribers and waiting. Sonara automates the audio-to-notation pipeline end to
            end, so a recording can become a readable score in minutes instead of weeks.
          </p>
        </Reveal>

        <Reveal delay={80} className="mt-14">
          <h3 className="mb-6 text-[1.3rem]">How the pipeline works</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {APPROACH.map(({ Icon, name, blurb }) => (
              <div
                key={name}
                className="rounded-(--radius-m) border border-border bg-surface p-5.5 shadow-(--shadow-s) transition-[border-color,box-shadow] hover:border-brand/40 hover:shadow-[0_0_0_1px_var(--brand-wash),0_8px_28px_-10px_var(--accent-glow,rgba(134,59,255,0.3))]"
              >
                <div className="mb-3 flex size-10 items-center justify-center rounded-full bg-brand-wash text-brand">
                  <Icon className="size-5" />
                </div>
                <h4 className="mb-1.5 text-[1.02rem] font-bold text-heading">{name}</h4>
                <p className="m-0 text-[0.9rem] leading-relaxed text-dim">{blurb}</p>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      <section id="functions" className="relative mx-auto max-w-[880px] px-6 py-28">
        <Reveal>
          <p className="mb-2 text-[0.82rem] font-bold tracking-[0.2em] text-brand uppercase">Functions</p>
          <h2 className="mb-5 text-[2rem]">What Sonara does</h2>
          <p className="max-w-[64ch] text-[1.02rem] leading-relaxed text-dim">
            Five tools, each usable standalone against a symbolic score or straight off an
            audio recording.
          </p>
        </Reveal>

        <Reveal delay={80} className="mt-10">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FUNCTIONS.map(({ Icon, name, blurb }) => (
              <div
                key={name}
                className="rounded-(--radius-m) border border-border bg-surface p-5.5 shadow-(--shadow-s) transition-[border-color,box-shadow] hover:border-brand/40 hover:shadow-[0_0_0_1px_var(--brand-wash),0_8px_28px_-10px_var(--accent-glow,rgba(134,59,255,0.3))]"
              >
                <div className="mb-3 flex size-10 items-center justify-center rounded-full bg-brand-wash text-brand">
                  <Icon className="size-5" />
                </div>
                <h4 className="mb-1.5 text-[1.02rem] font-bold text-heading">{name}</h4>
                <p className="m-0 text-[0.9rem] leading-relaxed text-dim">{blurb}</p>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={160} className="mt-14 flex justify-center">
          <a
            href="#/app"
            className="inline-flex items-center gap-2 rounded-(--radius-s) bg-gradient-to-r from-[#863bff] to-[#47bfff] px-7 py-3.5 text-[1rem] font-bold text-white shadow-[0_4px_20px_rgba(134,59,255,0.4)] transition-transform hover:-translate-y-0.5"
          >
            Open the tool
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="size-[1.1rem]">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </a>
        </Reveal>
      </section>

      <footer className="mx-auto max-w-[55ch] px-6 pb-16 text-center text-[0.78rem] text-dim">
        <p>Best-effort ML pipeline &middot; accuracy varies by material &middot; built for accessibility, not a replacement for a human transcriber</p>
      </footer>
    </div>
  )
}
