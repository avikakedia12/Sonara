import { useState } from 'react'
import PianoHero from './components/PianoHero'
import TranscribePage from './pages/TranscribePage'
import BraillePage from './pages/BraillePage'
import TransposePage from './pages/TransposePage'
import DescribePage from './pages/DescribePage'
import DifficultyPage from './pages/DifficultyPage'
import { TranscribeIcon, BrailleIcon, TransposeIcon, DescribeIcon, DifficultyIcon } from './components/Icons'
import { Tabs, TabsList, TabsTrigger, TabsContent } from './components/ui/tabs'
import { Card, CardContent } from './components/ui/card'

const TABS = [
  { id: 'transcribe', label: 'Transcribe', Icon: TranscribeIcon, Page: TranscribePage },
  { id: 'braille', label: 'Braille', Icon: BrailleIcon, Page: BraillePage },
  { id: 'transpose', label: 'Transpose', Icon: TransposeIcon, Page: TransposePage },
  { id: 'describe', label: 'Describe', Icon: DescribeIcon, Page: DescribePage },
  { id: 'difficulty', label: 'Difficulty', Icon: DifficultyIcon, Page: DifficultyPage },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('transcribe')

  return (
    <div className="relative mx-auto min-h-svh max-w-[880px] px-6 pt-10 pb-16" data-tab={activeTab}>
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-x-[-10%] top-[-12%] -z-10 h-[30rem] opacity-15 blur-[70px] transition-[background] duration-400"
        style={{ background: 'radial-gradient(closest-side, var(--brand), transparent 72%)' }}
      />

      <div
        className="relative -mt-10 mb-10 ml-[calc(50%-50vw)] flex min-h-svh w-screen items-center justify-center overflow-hidden bg-[radial-gradient(60%_50%_at_50%_20%,rgba(109,40,217,0.16),transparent_70%),radial-gradient(50%_45%_at_50%_85%,rgba(249,115,22,0.12),transparent_70%),var(--bg-canvas)] dark:bg-[radial-gradient(60%_50%_at_50%_20%,rgba(167,139,250,0.22),transparent_70%),radial-gradient(50%_45%_at_50%_85%,rgba(251,146,60,0.16),transparent_70%),var(--bg-canvas)]"
      >
        <PianoHero />
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex justify-center">
          <TabsList className="mx-auto mb-8 h-auto flex-wrap justify-center gap-1 rounded-full border border-border bg-background p-1.5 shadow-(--shadow-s)">
            {TABS.map(({ id, label, Icon }) => (
              <TabsTrigger
                key={id}
                value={id}
                className="gap-1.5 rounded-full px-4 py-2 text-[0.92rem] font-semibold text-dim transition-all hover:bg-brand-wash hover:text-brand data-active:scale-[1.04] data-active:border-transparent data-active:bg-brand data-active:text-brand-contrast data-active:shadow-(--shadow-s)"
              >
                <Icon className="size-[1.05rem]" />
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {TABS.map(({ id, Page }) => (
          <TabsContent key={id} value={id}>
            <Card className="rounded-(--radius-l) py-0 shadow-(--shadow-m)">
              <CardContent className="px-9 py-9">
                <Page />
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>

      <footer className="mx-auto mt-10 max-w-[55ch] text-center text-[0.78rem] text-dim">
        <p>Best-effort ML pipeline &middot; accuracy varies by material &middot; built for accessibility, not a replacement for a human transcriber</p>
      </footer>
    </div>
  )
}
