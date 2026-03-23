import React, { useEffect, useState } from 'react'
import { Plus, GraduationCap, Trash2, ArrowLeft, Bot, Settings, Wrench, Loader2, ChevronDown, ChevronRight, Users } from 'lucide-react'
import { useSchoolStore } from '@/store/schoolStore'
import { useModelStore } from '@/store/modelStore'
import { useToolStore } from '@/store/toolStore'
import type { ModelConfig } from '@/types/model'
import ConfirmDialog from '@/components/ConfirmDialog'

export default function AgentSchool() {
  const {
    schools,
    error,
    createSchool,
    deleteSchool,
    addAgentToSchool,
    removeAgentFromSchool,
    loadSchools,
    isAgentInstantiated,
    isAgentInstantiating,
    loadAllAgentInstantiationStatus,
    instantiateAgent
  } = useSchoolStore()

  const { models } = useModelStore()
  const { scanTools } = useToolStore()
  const [draggedAgent, setDraggedAgent] = useState<ModelConfig | null>(null)
  const [dragSource, setDragSource] = useState<'agent-list' | 'school' | null>(null)
  const [newSchoolName, setNewSchoolName] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showDeleteSchoolConfirm, setShowDeleteSchoolConfirm] = useState(false)
  const [schoolToDelete, setSchoolToDelete] = useState<{ id: string; name: string } | null>(null)
  const [showDeleteAgentConfirm, setShowDeleteAgentConfirm] = useState(false)
  const [agentToDelete, setAgentToDelete] = useState<{ schoolId: string; agentId: string; agentName: string } | null>(null)
  const [expandedToolListSchoolId, setExpandedToolListSchoolId] = useState<string | null>(null)
  const [creatingAgents, setCreatingAgents] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadSchools()
    scanTools()
  }, [loadSchools, scanTools])

  useEffect(() => {
    if (schools.length > 0) {
      const agentIds = schools.flatMap(school => 
        (school.agents || []).map(agent => agent.agent_id)
      )
      if (agentIds.length > 0) {
        loadAllAgentInstantiationStatus(agentIds)
      }
    }
  }, [schools, loadAllAgentInstantiationStatus])

  const handleCreateSchool = async () => {
    if (!newSchoolName.trim()) return

    try {
      await createSchool(newSchoolName.trim())
      setNewSchoolName('')
      setShowCreateDialog(false)
    } catch (error) {
      console.error('Failed to create school:', error)
      alert('创建School失败')
    }
  }

  const handleDeleteSchoolClick = (schoolId: string, schoolName: string) => {
    setSchoolToDelete({ id: schoolId, name: schoolName })
    setShowDeleteSchoolConfirm(true)
  }

  const handleConfirmDeleteSchool = async () => {
    if (!schoolToDelete) return

    try {
      await deleteSchool(schoolToDelete.id)
    } catch (error) {
      console.error('Failed to delete school:', error)
      alert('删除School失败')
    } finally {
      setShowDeleteSchoolConfirm(false)
      setSchoolToDelete(null)
    }
  }

  const handleCancelDeleteSchool = () => {
    setShowDeleteSchoolConfirm(false)
    setSchoolToDelete(null)
  }

  const handleDeleteAgentClick = (schoolId: string, agentId: string, agentName: string) => {
    setAgentToDelete({ schoolId, agentId, agentName })
    setShowDeleteAgentConfirm(true)
  }

  const handleConfirmDeleteAgent = async () => {
    if (!agentToDelete) return

    try {
      await removeAgentFromSchool(agentToDelete.schoolId, agentToDelete.agentId)
    } catch (error) {
      console.error('Failed to remove agent from school:', error)
      alert('从School移除Agent失败')
    } finally {
      setShowDeleteAgentConfirm(false)
      setAgentToDelete(null)
    }
  }

  const handleCancelDeleteAgent = () => {
    setShowDeleteAgentConfirm(false)
    setAgentToDelete(null)
  }

  // Agent拖拽开始
  const handleAgentDragStart = (e: React.DragEvent, agent: ModelConfig) => {
    setDraggedAgent(agent)
    setDragSource('agent-list')
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'agent', agentId: agent.id }))
  }

  // 拖拽结束
  const handleDragEnd = () => {
    setDraggedAgent(null)
    setDragSource(null)
  }

  // 允许拖拽到School
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    // 拒绝从其他school的拖动
    if (dragSource === 'school') {
      e.dataTransfer.dropEffect = 'none'
    } else {
      e.dataTransfer.dropEffect = 'move'
    }
  }

  // 拖拽到School
  const handleDropOnSchool = async (e: React.DragEvent, schoolId: string) => {
    e.preventDefault()

    // 只接受从agent列表的拖动，拒绝从其他school的拖动
    if (dragSource !== 'agent-list') {
      handleDragEnd()
      return
    }

    if (draggedAgent) {
      // 从左侧Agent列表拖入School
      const agentId = draggedAgent.id
      // 添加到创建中状态
      setCreatingAgents(prev => new Set(prev).add(agentId))

      try {
        await addAgentToSchool(
          schoolId,
          agentId,
          draggedAgent.name,
          draggedAgent
        )
      } catch (error) {
        console.error('Failed to add agent to school:', error)
        alert('添加Agent到School失败')
      } finally {
        // 无论成功或失败，都从创建中状态移除
        setCreatingAgents(prev => {
          const newSet = new Set(prev)
          newSet.delete(agentId)
          return newSet
        })
      }
    }

    handleDragEnd()
  }

  const getProviderIcon = (provider: string) => {
    const icons: Record<string, string> = {
      openai: '🤖',
      anthropic: '🧠',
      ollama: '🦙',
      custom: '⚙️'
    }
    return icons[provider] || '📦'
  }

  const getAgentById = (agentId: string) => {
    return models.find(m => m.id === agentId)
  }

  const toggleToolList = (schoolId: string) => {
    setExpandedToolListSchoolId(expandedToolListSchoolId === schoolId ? null : schoolId)
  }

  const handleAgentClick = async (agentId: string) => {
    const isInstantiated = isAgentInstantiated(agentId)
    const isInstantiating = isAgentInstantiating(agentId)
    
    if (!isInstantiated && !isInstantiating) {
      try {
        await instantiateAgent(agentId)
      } catch (error) {
        console.error('Failed to instantiate agent:', error)
        alert('实例化Agent失败')
      }
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => {
                const event = new CustomEvent('route-change', {
                  detail: { route: 'chat' as const }
                })
                window.dispatchEvent(event)
              }}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center space-x-3">
              <GraduationCap className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-800">AgentSchool</h1>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                const event = new CustomEvent('route-change', {
                  detail: { route: 'agent-team' as const }
                })
                window.dispatchEvent(event)
              }}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 shadow-sm hover:bg-gray-50 transition-colors font-medium flex items-center space-x-2"
            >
              <Users className="w-4 h-4" />
              <span>Agent Team</span>
            </button>
            <button
              onClick={() => {
                const event = new CustomEvent('route-change', {
                  detail: { route: 'school-config' as const }
                })
                window.dispatchEvent(event)
              }}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 shadow-sm hover:bg-gray-50 transition-colors font-medium flex items-center space-x-2"
            >
              <Settings className="w-4 h-4" />
              <span>School配置</span>
            </button>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="px-4 py-2 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover transition-colors font-medium flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>新建School</span>
            </button>
          </div>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-danger-50 border border-danger-200 text-danger-700 rounded-lg">
            {error}
          </div>
        )}

        <div className="flex gap-6">
          {/* 左侧Agent列表 */}
          <div className="w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <h2 className="font-semibold text-gray-800">Agent列表</h2>
                <p className="text-xs text-gray-500 mt-1">拖拽Agent到School中，若agent配置有更改请重新拖入（模型需要支持functioncalling）</p>
              </div>
              <div className="p-4 space-y-2 max-h-[600px] overflow-y-auto">
                {models.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <Bot className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">暂无Agent配置</p>
                  </div>
                ) : (
                  models.map((model) => {
                    const isInSchool = schools.some(school =>
                      school.agents?.some(agent => agent.agent_id === model.id)
                    )

                    return (
                      <div
                        key={model.id}
                        draggable={!isInSchool}
                        onDragStart={(e) => handleAgentDragStart(e, model)}
                        onDragEnd={handleDragEnd}
                        className={`p-3 rounded-lg border transition-all cursor-move ${
                          isInSchool
                            ? 'bg-gray-100 border-gray-200 opacity-50 cursor-not-allowed'
                            : 'bg-white border-gray-200 hover:border-primary-300 hover:shadow-sm'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-primary-100 flex items-center justify-center text-lg rounded-full">
                            {getProviderIcon(model.provider)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm truncate">{model.name}</p>
                            <p className="text-xs text-gray-500 truncate">{model.model}</p>
                            {isInSchool && (
                              <p className="text-xs text-primary-600 mt-1">已在School中</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </div>

          {/* 右侧School列表 */}
          <div className="flex-1">
            {schools.length === 0 ? (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <GraduationCap className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-semibold text-gray-700 mb-2">还没有School</h3>
                <p className="text-gray-500 mb-4">创建您的第一个School来管理Agent</p>
                <button
                  onClick={() => setShowCreateDialog(true)}
                  className="px-4 py-2 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover transition-colors font-medium inline-flex items-center space-x-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>创建School</span>
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {schools.map((school) => (
                  <div
                    key={school.id}
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDropOnSchool(e, school.id)}
                    className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:border-primary-300 transition-colors"
                  >
                    <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <GraduationCap className="w-5 h-5 text-primary-600" />
                        <h3 className="font-semibold text-gray-800">{school.name}</h3>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleToolList(school.id)
                          }}
                          className="px-3 py-1.5 text-sm bg-transparent border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg transition-colors flex items-center space-x-1"
                        >
                          {expandedToolListSchoolId === school.id ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                          <Wrench className="w-3.5 h-3.5" />
                          <span>工具列表</span>
                        </button>
                        <button
                          onClick={() => handleDeleteSchoolClick(school.id, school.name)}
                          className="p-1 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded transition-colors"
                          title="删除School"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    <div className="p-4 min-h-[200px]">
                      {expandedToolListSchoolId === school.id ? (
                        <div className="space-y-2">
                          {(!school.tools || school.tools.length === 0) ? (
                            <div className="h-full flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-lg py-8">
                              <p className="text-sm">暂无工具，请前往School配置页面添加</p>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {school.tools.map((tool) => (
                                <div
                                  key={tool.tool_name}
                                  className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                                >
                                  <div className="flex-1 min-w-0">
                                    <p className="font-medium text-sm">{tool.tool_name}</p>
                                    <p className="text-xs text-gray-500 truncate">{tool.tool_description}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        (!school.agents || school.agents.length === 0) ? (
                          <div className="h-full flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
                            <p className="text-sm">拖拽Agent到这里</p>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {school.agents.map((agent) => {
                              const agentConfig = getAgentById(agent.agent_id)
                              const isCreating = creatingAgents.has(agent.agent_id)
                              const isInstantiated = isAgentInstantiated(agent.agent_id)
                              const isInstantiating = isAgentInstantiating(agent.agent_id)
                              const isNotInstantiated = !isInstantiated && !isCreating && !isInstantiating
                              
                              return (
                                <div
                                  key={agent.agent_id}
                                  draggable={false}
                                  onClick={() => handleAgentClick(agent.agent_id)}
                                  className={`p-3 rounded-lg border hover:shadow-sm transition-all cursor-pointer ${
                                    isNotInstantiated
                                      ? 'bg-red-50 border-red-200 hover:border-red-300'
                                      : 'bg-gray-50 border-gray-200 hover:border-primary-300'
                                  }`}
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-3">
                                      <div className={`w-8 h-8 flex items-center justify-center text-lg rounded-full ${
                                        isNotInstantiated ? 'bg-red-100' : 'bg-primary-100'
                                      }`}>
                                        {isInstantiating ? (
                                          <Loader2 className="w-5 h-5 animate-spin text-red-600" />
                                        ) : agentConfig ? (
                                          getProviderIcon(agentConfig.provider)
                                        ) : (
                                          '📦'
                                        )}
                                      </div>
                                      <div>
                                        <p className="font-medium text-sm">{agent.agent_name}</p>
                                        <p className={`text-xs ${
                                          isNotInstantiated ? 'text-red-600' : 'text-gray-500'
                                        }`}>
                                          {isCreating ? '创建中...' : 
                                           isInstantiating ? '实例化中...' :
                                           isNotInstantiated ? '未实例化，点击初始化' :
                                           (agentConfig?.model || 'Unknown')}
                                        </p>
                                      </div>
                                    </div>
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        handleDeleteAgentClick(school.id, agent.agent_id, agent.agent_name)
                                      }}
                                      className="p-1 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded transition-colors"
                                      title="移除Agent"
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </button>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 创建School对话框 */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">创建新School</h3>
            <input
              type="text"
              value={newSchoolName}
              onChange={(e) => setNewSchoolName(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleCreateSchool()
                }
              }}
              placeholder="输入School名称"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 mb-4"
              autoFocus
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowCreateDialog(false)
                  setNewSchoolName('')
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleCreateSchool}
                disabled={!newSchoolName.trim()}
                className="px-4 py-2 bg-gradient-primary text-white rounded-lg hover:shadow-elegant-hover transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 删除School确认对话框 */}
      <ConfirmDialog
        isOpen={showDeleteSchoolConfirm}
        title="删除School"
        message={`确定要删除School【${schoolToDelete?.name}】吗？`}
        confirmText="确定"
        cancelText="取消"
        onConfirm={handleConfirmDeleteSchool}
        onCancel={handleCancelDeleteSchool}
        type="danger"
      />

      {/* 从School移除Agent确认对话框 */}
      <ConfirmDialog
        isOpen={showDeleteAgentConfirm}
        title="移除Agent"
        message={`确定要将Agent【${agentToDelete?.agentName}】从School中移除吗？`}
        confirmText="确定"
        cancelText="取消"
        onConfirm={handleConfirmDeleteAgent}
        onCancel={handleCancelDeleteAgent}
        type="danger"
      />
    </div>
  )
}
