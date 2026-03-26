import type { RunHistoryEntry } from '../mocks/history'

export default function RunHistory({ history }: { history: RunHistoryEntry[] }) {
  return (
    <div className="mx-6 mb-6 bg-card rounded-xl border border-border p-4 space-y-3">
      <h2 className="text-lg font-bold text-white">📊 실행 히스토리</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-inactive border-b border-border">
              <th className="py-2 px-2">#</th>
              <th className="py-2 px-2">시간</th>
              <th className="py-2 px-2">상태</th>
              <th className="py-2 px-2">설명</th>
              <th className="py-2 px-2">소요시간</th>
              <th className="py-2 px-2">LLM</th>
            </tr>
          </thead>
          <tbody>
            {history.map(h => (
              <tr key={h.run_id} className="border-b border-border/50 hover:bg-card-hover transition-colors">
                <td className="py-2 px-2 text-gray-400">{h.run_id}</td>
                <td className="py-2 px-2 text-gray-300 font-mono text-xs">{new Date(h.started_at).toLocaleString('ko-KR')}</td>
                <td className="py-2 px-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${h.status === 'success' ? 'bg-success text-black' : 'bg-failed text-white'}`}>
                    {h.status.toUpperCase()}
                  </span>
                </td>
                <td className="py-2 px-2 text-white">{h.description}</td>
                <td className="py-2 px-2 text-gray-300">{h.duration_minutes}분</td>
                <td className="py-2 px-2 text-gray-300">{h.llm_calls}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
