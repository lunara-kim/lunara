import Header from './components/Header'
import PipelineStatus from './components/PipelineStatus'
import PipelineControl from './components/PipelineControl'
import TaskTable from './components/TaskTable'
import AgentConfig from './components/AgentConfig'
import LogViewer from './components/LogViewer'
import StatsBar from './components/StatsBar'
import RunHistory from './components/RunHistory'
import { useDashboard } from './hooks/useDashboard'

export default function App() {
  const { progress, tasks, agents, logs, history, isLive, isPipelineRunning, triggerPipeline, cancelPipeline } = useDashboard()

  return (
    <div className="min-h-screen text-gray-100">
      <Header updatedAt={progress.updated_at} isLive={isLive} />
      <PipelineStatus progress={progress} agents={agents} />
      <PipelineControl isRunning={isPipelineRunning} onTrigger={triggerPipeline} onCancel={cancelPipeline} />

      {/* Main content: 2-column on lg */}
      <div className="mx-6 mt-4 grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-4">
        <TaskTable tasks={tasks} />
        <div className="space-y-4">
          <AgentConfig agents={agents} currentAgent={progress.current_agent} />
          <LogViewer logs={logs} />
        </div>
      </div>

      <div className="mt-4">
        <StatsBar />
      </div>

      <div className="mt-4">
        <RunHistory history={history} />
      </div>
    </div>
  )
}
