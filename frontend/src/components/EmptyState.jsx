export default function EmptyState({ icon, text }) {
  return (
    <div className="flex flex-col items-center gap-2.5 px-4 py-11 text-center text-dim">
      <span className="text-[2.1rem] opacity-70">{icon}</span>
      <p className="m-0 max-w-[32ch] text-[0.9rem]">{text}</p>
    </div>
  )
}
