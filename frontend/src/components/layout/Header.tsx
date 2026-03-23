import { Settings, GraduationCap } from 'lucide-react'

export default function Header() {
  const handleSettingsClick = () => {
    const event = new CustomEvent('route-change', {
      detail: { route: 'agent-management' as const }
    })
    window.dispatchEvent(event)
  }

  const handleAgentSchoolClick = () => {
    const event = new CustomEvent('route-change', {
      detail: { route: 'agent-school' as const }
    })
    window.dispatchEvent(event)
  }

  return (
    <div className="h-14 bg-white flex items-center justify-between px-6 border-b border-gray-200">
      <div className="flex items-center space-x-4">
        <h2 className="text-lg font-semibold text-gray-800">Chat</h2>
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={handleAgentSchoolClick}
          className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors flex items-center space-x-2"
          title="AgentSchool"
        >
          <GraduationCap className="w-5 h-5" />
          <span>Agentschool</span>
        </button>
        <button
          onClick={handleSettingsClick}
          className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors"
          title="Agent配置"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
