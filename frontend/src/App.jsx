import { useState } from 'react'
import PianoHero from './components/PianoHero'
import TranscribePage from './pages/TranscribePage'
import BraillePage from './pages/BraillePage'
import TransposePage from './pages/TransposePage'
import DescribePage from './pages/DescribePage'
import DifficultyPage from './pages/DifficultyPage'
import { TranscribeIcon, BrailleIcon, TransposeIcon, DescribeIcon, DifficultyIcon } from './components/Icons'
import './App.css'

const TABS = [
  { id: 'transcribe', label: 'Transcribe', Icon: TranscribeIcon, Page: TranscribePage },
  { id: 'braille', label: 'Braille', Icon: BrailleIcon, Page: BraillePage },
  { id: 'transpose', label: 'Transpose', Icon: TransposeIcon, Page: TransposePage },
  { id: 'describe', label: 'Describe', Icon: DescribeIcon, Page: DescribePage },
  { id: 'difficulty', label: 'Difficulty', Icon: DifficultyIcon, Page: DifficultyPage },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('transcribe')
  const ActivePage = TABS.find((t) => t.id === activeTab).Page

  return (
    <div className="app" data-tab={activeTab}>
      <div className="app-glow" aria-hidden="true" />

      <div className="hero">
        <PianoHero />
        <header className="app-header">
          <div className="brand">
            <span className="brand-mark">
              <TranscribeIcon />
            </span>
            <h1>Sonara</h1>
          </div>
          <p className="tagline">
            <span>Hear it.</span> <span>See it.</span> <span>Feel it.</span>
          </p>
          <p className="tagline-sub">turning a recording into music someone can read</p>
        </header>
      </div>

      <div className="tabs-wrap">
        <nav className="tabs">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              className={id === activeTab ? 'tab active' : 'tab'}
              onClick={() => setActiveTab(id)}
            >
              <Icon />
              {label}
            </button>
          ))}
        </nav>
      </div>

      <main className="app-main">
        <ActivePage key={activeTab} />
      </main>

      <footer className="app-footer">
        <p>Best-effort ML pipeline &middot; accuracy varies by material &middot; built for accessibility, not a replacement for a human transcriber</p>
      </footer>
    </div>
  )
}
