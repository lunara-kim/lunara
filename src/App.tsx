import Header from './components/Header'
import PipelineStatus from './components/PipelineStatus'
import TaskTable from './components/TaskTable'
import AgentConfig from './components/AgentConfig'
import LogViewer from './components/LogViewer'
import StatsBar from './components/StatsBar'
import RunHistory from './components/RunHistory'
import { mockProgress } from './mocks/progress'
import { mockTasks } from './mocks/tasks'
import { mockAgents } from './mocks/agents'
import { mockLogs } from './mocks/logs'
import { mockHistory } from './mocks/history'

export default function App() {
  return (
    <div className="min-h-screen text-gray-100">
      <Header updatedAt={mockProgress.updated_at} />
      <PipelineStatus progress={mockProgress} agents={mockAgents} />

      {/* Main content: 2-column on lg */}
      <div className="mx-6 mt-4 grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-4">
        <TaskTable tasks={mockTasks} />
        <div className="space-y-4">
          <AgentConfig agents={mockAgents} currentAgent={mockProgress.current_agent} />
          <LogViewer logs={mockLogs} />
        </div>
      </div>

      <div className="mt-4">
        <StatsBar />
      </div>

      <div className="mt-4">
        <RunHistory history={mockHistory} />
      </div>
    </div>
  )
}
