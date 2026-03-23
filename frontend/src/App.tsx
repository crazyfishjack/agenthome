import React, { useEffect } from 'react'
import { useModelStore } from './store/modelStore'
import { useSchoolStore } from './store/schoolStore'
import { modelsApi } from './api/models'
import Layout from './components/layout/Layout'
import AgentManagement from './pages/AgentManagement'
import AgentSchool from './pages/AgentSchool'
import SchoolConfig from './pages/SchoolConfig'
import AgentTeam from './pages/AgentTeam'

function App() {
  const setModels = useModelStore((state) => state.setModels)
  const loadSchools = useSchoolStore((state) => state.loadSchools)
  const loadAllAgentSchools = useSchoolStore((state) => state.loadAllAgentSchools)
  const models = useModelStore((state) => state.models)
  const [currentRoute, setCurrentRoute] = React.useState<'chat' | 'agent-management' | 'agent-school' | 'school-config' | 'agent-team'>('chat')

  useEffect(() => {
    const initData = async () => {
      try {
        const models = await modelsApi.getConfigs()
        setModels(models as any)
      } catch (error) {
        console.error('Failed to initialize data:', error)
      }
    }

    initData()
  }, [setModels])

  // 加载schools和agent的school信息
  useEffect(() => {
    const loadSchoolData = async () => {
      try {
        await loadSchools()
        if (models.length > 0) {
          const agentIds = models.map(m => m.id)
          await loadAllAgentSchools(agentIds)
        }
      } catch (error) {
        console.error('Failed to load school data:', error)
      }
    }

    loadSchoolData()
  }, [loadSchools, loadAllAgentSchools, models.length])

  useEffect(() => {
    const handleRouteChange = (e: CustomEvent<{ route: 'chat' | 'agent-management' | 'agent-school' | 'school-config' | 'agent-team' }>) => {
      setCurrentRoute(e.detail.route)
    }

    window.addEventListener('route-change', handleRouteChange as EventListener)
    return () => {
      window.removeEventListener('route-change', handleRouteChange as EventListener)
    }
  }, [])

  if (currentRoute === 'agent-management') {
    return <AgentManagement />
  }

  if (currentRoute === 'agent-school') {
    return <AgentSchool />
  }

  if (currentRoute === 'school-config') {
    return <SchoolConfig />
  }

  if (currentRoute === 'agent-team') {
    return <AgentTeam />
  }

  return <Layout />
}

export default App
