import { useState } from 'react'

interface Props {
  isRunning: boolean
  onTrigger: (inputText: string) => Promise<{ status: string; message: string }>
  onCancel: () => Promise<{ status: string; message?: string }>
}

export default function PipelineControl({ isRunning, onTrigger, onCancel }: Props) {
  const [inputText, setInputText] = useState('')
  const [statusMsg, setStatusMsg] = useState<string | null>(null)

  async function handleRun() {
    if (!inputText.trim()) return
    try {
      const res = await onTrigger(inputText)
      setStatusMsg(res.message)
    } catch {
      setStatusMsg('파이프라인 실행 요청 실패')
    }
  }

  async function handleCancel() {
    try {
      const res = await onCancel()
      setStatusMsg(res.message ?? '취소됨')
    } catch {
      setStatusMsg('취소 요청 실패')
    }
  }

  return (
    <div className="mx-6 mt-4 rounded-xl border border-gray-700 bg-gray-800/60 p-4">
      <h2 className="mb-2 text-sm font-semibold text-gray-300">파이프라인 실행</h2>
      <textarea
        className="w-full rounded-lg border border-gray-600 bg-gray-900 p-3 text-sm text-gray-100 placeholder-gray-500 focus:border-emerald-500 focus:outline-none"
        rows={3}
        placeholder="요구사항을 입력하세요..."
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        disabled={isRunning}
      />
      <div className="mt-2 flex items-center gap-3">
        <button
          onClick={handleRun}
          disabled={isRunning || !inputText.trim()}
          className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-[#2ecc71] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isRunning ? '실행 중...' : '🚀 파이프라인 실행'}
        </button>
        {isRunning && (
          <button
            onClick={handleCancel}
            className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-[#ef4444]"
          >
            ⏹ 취소
          </button>
        )}
        {statusMsg && (
          <span className="text-sm text-gray-400">{statusMsg}</span>
        )}
      </div>
    </div>
  )
}
