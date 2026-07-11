import { useState } from 'react'
import TranscribePage from './pages/TranscribePage'
import BraillePage from './pages/BraillePage'
import TransposePage from './pages/TransposePage'
import DescribePage from './pages/DescribePage'
import './App.css'

const TABS = [
  { id: 'transcribe', label: 'Transcribe', Page: TranscribePage },
  { id: 'braille', label: 'Braille', Page: BraillePage },
  { id: 'transpose', label: 'Transpose', Page: TransposePage },
  { id: 'describe', label: 'Describe', Page: DescribePage },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('transcribe')
  const ActivePage = TABS.find((t) => t.id === activeTab).Page

  return (
    <div className="app">
      <header className="app-header">
        <h1>Sonara</h1>
        <p className="tagline">Audio-to-Braille music accessibility pipeline</p>
      </header>

      <nav className="tabs">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            className={id === activeTab ? 'tab active' : 'tab'}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        <ActivePage />
      </main>
    </div>
  )
}
