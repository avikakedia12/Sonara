export default function EmptyState({ icon, text }) {
  return (
    <div className="empty-state">
      <span className="empty-state-icon">{icon}</span>
      <p>{text}</p>
    </div>
  )
}
