import { useState } from 'react'
import TranscribePage from './pages/TranscribePage'
import BraillePage from './pages/BraillePage'
import TransposePage from './pages/TransposePage'
import DescribePage from './pages/DescribePage'
import { TranscribeIcon, BrailleIcon, TransposeIcon, DescribeIcon } from './components/Icons'
import './App.css'

const TABS = [
  { id: 'transcribe', label: 'Transcribe', Icon: TranscribeIcon, Page: TranscribePage },
  { id: 'braille', label: 'Braille', Icon: BrailleIcon, Page: BraillePage },
  { id: 'transpose', label: 'Transpose', Icon: TransposeIcon, Page: TransposePage },
  { id: 'describe', label: 'Describe', Icon: DescribeIcon, Page: DescribePage },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('transcribe')
  const ActivePage = TABS.find((t) => t.id === activeTab).Page

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">
            <TranscribeIcon />
          </span>
          <h1>Sonara</h1>
        </div>
        <p className="tagline">turning a recording into music someone can read</p>
      </header>

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
    </div>
  )
}
