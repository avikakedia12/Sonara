import { Progress } from '@/components/ui/progress'

/** Rotating status message + fake progress bar shown under the submit
 * button while an action is in flight. See useSimulatedProgress for why
 * the percentage is simulated rather than real. */
export default function LoadingProgress({ message, progress }) {
  return (
    <div className="-mt-1.5 flex flex-col gap-1.5 animate-fade-in">
      <div className="flex items-center justify-between text-[0.85rem] text-dim">
        <span>{message}</span>
        <span className="tabular-nums">{progress}%</span>
      </div>
      <Progress value={progress} className="h-1.5" />
    </div>
  )
}
