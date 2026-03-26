export default function Header({ updatedAt }: { updatedAt: string | null }) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border">
      <h1 className="text-2xl font-bold text-white">🤖 AgentCrew Dashboard</h1>
      <span className="text-sm text-inactive">
        마지막 업데이트: {updatedAt ?? '-'}
      </span>
    </header>
  )
}
