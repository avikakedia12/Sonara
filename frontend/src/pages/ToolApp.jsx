import { useState } from 'react'
import TranscribePage from './TranscribePage'
import BraillePage from './BraillePage'
import TransposePage from './TransposePage'
import DescribePage from './DescribePage'
import DifficultyPage from './DifficultyPage'
import { TranscribeIcon, BrailleIcon, TransposeIcon, DescribeIcon, DifficultyIcon } from '../components/Icons'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs'
import { Card, CardContent } from '../components/ui/card'

const TABS = [
  { id: 'transcribe', label: 'Transcribe', Icon: TranscribeIcon, Page: TranscribePage },
  { id: 'braille', label: 'Braille', Icon: BrailleIcon, Page: BraillePage },
  { id: 'transpose', label: 'Transpose', Icon: TransposeIcon, Page: TransposePage },
  { id: 'describe', label: 'Describe', Icon: DescribeIcon, Page: DescribePage },
  { id: 'difficulty', label: 'Difficulty', Icon: DifficultyIcon, Page: DifficultyPage },
]

export default function ToolApp() {
  const [activeTab, setActiveTab] = useState('transcribe')

  return (
    <div className="relative mx-auto min-h-svh max-w-[880px] px-6 pt-10 pb-16" data-tab={activeTab}>
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-x-[-10%] top-[-12%] -z-10 h-[30rem] opacity-15 blur-[70px] transition-[background] duration-400"
        style={{ background: 'radial-gradient(closest-side, var(--brand), transparent 72%)' }}
      />

      <a
        href="#/"
        className="mb-8 inline-flex items-center gap-1.5 text-[0.85rem] font-semibold text-dim transition-colors hover:text-brand"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-[1rem]">
          <path d="M11 19l-7-7 7-7M4 12h16" />
        </svg>
        sonara
      </a>

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
