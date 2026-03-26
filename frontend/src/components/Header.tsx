export default function Header({ updatedAt, isLive }: { updatedAt: string | null; isLive?: boolean }) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-white">🤖 AgentCrew Dashboard</h1>
        {isLive !== undefined && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            isLive
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}>
            {isLive ? '🟢 Live' : '🔴 Mock'}
          </span>
        )}
      </div>
      <span className="text-sm text-inactive">
        마지막 업데이트: {updatedAt ?? '-'}
      </span>
    </header>
  )
}
