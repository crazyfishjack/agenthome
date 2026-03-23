import React, { useEffect, useState } from 'react'
import { ArrowLeft, Save, GraduationCap, Trash2, Sparkles, Zap, Settings, ChevronDown, ChevronRight, Wrench, Wand2, Cpu } from 'lucide-react'
import { useSchoolStore } from '@/store/schoolStore'
import { useToolStore } from '@/store/toolStore'
import { schoolsApi } from '@/api/schools'
import { mcpApi } from '@/api/mcp'
import ToolList from '@/components/ToolList'
import SkillList from '@/components/SkillList'
import MCPList from '@/components/MCPList'
import MCPConfigModal from '@/components/MCPConfigModal'
import type { ToolConfig } from '@/store/toolStore'
import type { School } from '@/types/school'
import type { MCPConfig } from '@/types/school'

export default function SchoolConfig() {
  const {
    schools,
    error,
    loadSchools
  } = useSchoolStore()

  const {
    tools,
    error: toolsError,
    scanTools
  } = useToolStore()

  const [draggedTool, setDraggedTool] = useState<ToolConfig | null>(null)
  const [draggedSkill, setDraggedSkill] = useState<any | null>(null)
  const [draggedMcp, setDraggedMcp] = useState<MCPConfig | null>(null)
  const [dragSource, setDragSource] = useState<'tool-list' | 'skill-list' | 'mcp-list' | 'school' | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [skills, setSkills] = useState<any[]>([])
  const [skillsError, setSkillsError] = useState<string | null>(null)
  const [mcps, setMcps] = useState<MCPConfig[]>([])
  const [mcpsError, setMcpsError] = useState<string | null>(null)
  const [showMcpConfigModal, setShowMcpConfigModal] = useState(false)
  const [activeTab, setActiveTab] = useState<'tools' | 'skills' | 'mcps'>('tools')
  const [collapsedSchools, setCollapsedSchools] = useState<Record<string, boolean>>({})

  useEffect(() => {
    loadSchools()
    scanTools()
    loadSkills()
    loadMcps()
  }, [loadSchools, scanTools])

  const loadSkills = async () => {
    try {
      const allSkills = await schoolsApi.getAllSkills()
      setSkills(allSkills)
    } catch (error) {
      console.error('Failed to load skills:', error)
      setSkillsError('加载 Skills 失败')
    }
  }

  const loadMcps = async () => {
    try {
      const allMcps = await mcpApi.getAll()
      setMcps(allMcps)
    } catch (error) {
      console.error('Failed to load mcps:', error)
      setMcpsError('加载 MCP 失败')
    }
  }

  // Tool拖拽开始
  const handleToolDragStart = (e: React.DragEvent, tool: ToolConfig) => {
    setDraggedTool(tool)
    setDragSource('tool-list')
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'tool', toolName: tool.tool_name }))
  }

  // Skill拖拽开始
  const handleSkillDragStart = (e: React.DragEvent, skill: any) => {
    setDraggedSkill(skill)
    setDragSource('skill-list')
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'skill', skillId: skill.skill_id }))
  }

  // MCP拖拽开始
  const handleMcpDragStart = (e: React.DragEvent, mcp: MCPConfig) => {
    setDraggedMcp(mcp)
    setDragSource('mcp-list')
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', JSON.stringify({ type: 'mcp', mcpId: mcp.mcp_id }))
  }

  // 拖拽结束
  const handleDragEnd = () => {
    setDraggedTool(null)
    setDraggedSkill(null)
    setDraggedMcp(null)
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
  const handleDropOnSchool = async (e: React.DragEvent, school: School) => {
    e.preventDefault()

    // 只接受从tool列表、skill列表或mcp列表的拖动，拒绝从其他school的拖动
    if (dragSource !== 'tool-list' && dragSource !== 'skill-list' && dragSource !== 'mcp-list') {
      handleDragEnd()
      return
    }

    if (draggedTool) {
      // 从左侧Tool列表拖入School
      const updatedSchools = schools.map(s => {
        if (s.id === school.id) {
          const existingToolNames = (s.tools || []).map(t => t.tool_name)
          if (!existingToolNames.includes(draggedTool.tool_name)) {
            return {
              ...s,
              tools: [...(s.tools || []), draggedTool]
            }
          }
        }
        return s
      })

      // 更新本地状态
      await updateSchoolToolsState(school.id, updatedSchools.find(s => s.id === school.id)?.tools || [])
    } else if (draggedSkill) {
      // 从左侧Skill列表拖入School
      const updatedSchools = schools.map(s => {
        if (s.id === school.id) {
          const existingSkillIds = (s.skills || []).map(sk => sk.skill_id)
          if (!existingSkillIds.includes(draggedSkill.skill_id)) {
            return {
              ...s,
              skills: [...(s.skills || []), {
                skill_id: draggedSkill.skill_id,
                enabled: true
              }]
            }
          }
        }
        return s
      })

      // 更新本地状态
      await updateSchoolSkillsState(school.id, updatedSchools.find(s => s.id === school.id)?.skills || [])
    } else if (draggedMcp) {
      // 从左侧MCP列表拖入School
      const updatedSchools = schools.map(s => {
        if (s.id === school.id) {
          const existingMcpIds = (s.mcps || []).map(m => m.mcp_id)
          if (!existingMcpIds.includes(draggedMcp.mcp_id)) {
            return {
              ...s,
              mcps: [...(s.mcps || []), {
                ...draggedMcp,
                enabled: true
              }]
            }
          }
        }
        return s
      })

      // 更新本地状态
      await updateSchoolMcpsState(school.id, updatedSchools.find(s => s.id === school.id)?.mcps || [])
    }

    handleDragEnd()
  }

  // 拖拽到空白区域（从School移除Tool）- 暂时禁用此功能
  // const handleDropOnEmpty = async (e: React.DragEvent) => {
  //   e.preventDefault()
  // 
  //   if (draggedSchoolTool) {
  //     const updatedSchools = schools.map(s => {
  //       if (s.id === draggedSchoolTool.schoolId) {
  //         return {
  //           ...s,
  //           tools: (s.tools || []).filter(t => t.tool_name !== draggedSchoolTool.tool.tool_name)
  //         }
  //       }
  //       return s
  //     })
  // 
  //     // 更新本地状态
  //     await updateSchoolToolsState(draggedSchoolTool.schoolId, updatedSchools.find(s => s.id === draggedSchoolTool.schoolId)?.tools || [])
  //   }
  // 
  //   handleDragEnd()
  // }

  // 更新School的工具列表
  const updateSchoolToolsState = async (schoolId: string, tools: ToolConfig[]) => {
    try {
      await schoolsApi.updateSchoolTools(schoolId, { tools })
      // 重新加载schools
      await loadSchools()
    } catch (error) {
      console.error('Failed to update school tools:', error)
      alert('更新School工具失败')
    }
  }

  // 更新School的Skills列表
  const updateSchoolSkillsState = async (schoolId: string, skills: any[]) => {
    try {
      await schoolsApi.updateSchoolSkills(schoolId, { skills })
      // 重新加载schools
      await loadSchools()
    } catch (error) {
      console.error('Failed to update school skills:', error)
      alert('更新School Skills失败')
    }
  }

  // 更新School的MCPs列表
  const updateSchoolMcpsState = async (schoolId: string, mcps: MCPConfig[]) => {
    try {
      await mcpApi.updateSchoolMcps(schoolId, { mcps })
      // 重新加载schools
      await loadSchools()
    } catch (error) {
      console.error('Failed to update school mcps:', error)
      alert('更新School MCP失败')
    }
  }

  // 切换Skill的启用/禁用状态
  const toggleSkillEnabled = async (schoolId: string, skillId: string, enabled: boolean) => {
    try {
      await schoolsApi.toggleSchoolSkill(schoolId, skillId, enabled)
      // 重新加载schools
      await loadSchools()
    } catch (error) {
      console.error('Failed to toggle skill:', error)
      alert('切换Skill状态失败')
    }
  }

  // 保存 MCP 配置
  const handleSaveMcp = async (data: {
    name: string
    description?: string
    mode: 'remote' | 'stdio'
    config: any
  }) => {
    try {
      await mcpApi.create(data)
      // 重新加载 MCP 列表
      await loadMcps()
    } catch (error) {
      console.error('Failed to save mcp:', error)
      alert('保存 MCP 失败')
      throw error
    }
  }

  // 删除 MCP
  const handleDeleteMcp = async (mcpId: string) => {
    try {
      await mcpApi.delete(mcpId)
      // 重新加载 MCP 列表
      await loadMcps()
      // 重新加载 schools（因为 MCP 已从所有 school 中移除）
      await loadSchools()
    } catch (error) {
      console.error('Failed to delete mcp:', error)
      alert('删除 MCP 失败')
    }
  }

  // 切换School折叠状态
  const toggleSchoolCollapse = (schoolId: string) => {
    setCollapsedSchools(prev => ({
      ...prev,
      [schoolId]: !prev[schoolId]
    }))
  }

  // 保存所有配置
  const handleSaveAll = async () => {
    setSaving(true)
    setSaveMessage(null)

    try {
      // 保存每个school的工具配置
      for (const school of schools) {
        if (school.tools && school.tools.length > 0) {
          await schoolsApi.updateSchoolTools(school.id, { tools: school.tools })
        }
      }

      setSaveMessage('保存成功！')
      setTimeout(() => setSaveMessage(null), 3000)
    } catch (error) {
      console.error('Failed to save all configs:', error)
      setSaveMessage('保存失败，请重试')
      setTimeout(() => setSaveMessage(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col" onDragOver={handleDragOver}>
      {/* 顶部导航 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => {
                const event = new CustomEvent('route-change', {
                  detail: { route: 'agent-school' as const }
                })
                window.dispatchEvent(event)
              }}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center space-x-3">
              <GraduationCap className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-800">School 配置</h1>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {saveMessage && (
              <span className={`text-sm ${saveMessage.includes('成功') ? 'text-success-600' : 'text-danger-600'}`}>
                {saveMessage}
              </span>
            )}
            <button
              onClick={() => setShowMcpConfigModal(true)}
              className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors font-medium flex items-center space-x-2"
            >
              <Settings className="w-4 h-4" />
              <span>配置 MCP</span>
            </button>
            <button
              onClick={handleSaveAll}
              disabled={saving}
              className="px-4 py-2 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover transition-colors font-medium flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? '保存中...' : '保存配置'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 错误提示 */}
      {(error || toolsError || skillsError || mcpsError) && (
        <div className="max-w-7xl mx-auto px-6 py-4 flex-shrink-0">
          {error && (
            <div className="mb-3 p-4 bg-danger-50 border border-danger-200 text-danger-700 rounded-lg">
              {error}
            </div>
          )}
          {toolsError && (
            <div className="mb-3 p-4 bg-danger-50 border border-danger-200 text-danger-700 rounded-lg">
              {toolsError}
            </div>
          )}
          {skillsError && (
            <div className="mb-3 p-4 bg-danger-50 border border-danger-200 text-danger-700 rounded-lg">
              {skillsError}
            </div>
          )}
          {mcpsError && (
            <div className="mb-3 p-4 bg-danger-50 border border-danger-200 text-danger-700 rounded-lg">
              {mcpsError}
            </div>
          )}
        </div>
      )}

      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden max-w-7xl mx-auto w-full px-6 pb-6">
        {/* 左侧Tool、Skill和MCP列表 - 三合一 */}
        <div className="w-80 flex-shrink-0 flex flex-col bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {/* Tab切换 */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('tools')}
              className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center space-x-2 transition-colors ${
                activeTab === 'tools'
                  ? 'text-primary-600 bg-primary-50 border-b-2 border-primary-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Wrench className="w-4 h-4" />
              <span>工具</span>
            </button>
            <button
              onClick={() => setActiveTab('skills')}
              className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center space-x-2 transition-colors ${
                activeTab === 'skills'
                  ? 'text-primary-600 bg-primary-50 border-b-2 border-primary-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Wand2 className="w-4 h-4" />
              <span>Skills</span>
            </button>
            <button
              onClick={() => setActiveTab('mcps')}
              className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center space-x-2 transition-colors ${
                activeTab === 'mcps'
                  ? 'text-primary-600 bg-primary-50 border-b-2 border-primary-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <Cpu className="w-4 h-4" />
              <span>MCPs</span>
            </button>
          </div>

          {/* 列表内容 - 独立滚动 */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'tools' && (
              <ToolList
                tools={tools}
                onToolDragStart={handleToolDragStart}
                onToolDragEnd={handleDragEnd}
              />
            )}
            {activeTab === 'skills' && (
              <SkillList
                skills={skills}
                onSkillDragStart={handleSkillDragStart}
                onSkillDragEnd={handleDragEnd}
              />
            )}
            {activeTab === 'mcps' && (
              <MCPList
                mcps={mcps}
                onMcpDragStart={handleMcpDragStart}
                onMcpDragEnd={handleDragEnd}
                onMcpDelete={handleDeleteMcp}
              />
            )}
          </div>
        </div>

        {/* 右侧School列表 - 固定高度容器 */}
        <div className="flex-1 ml-6 overflow-hidden">
          {schools.length === 0 ? (
            <div className="h-full bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center flex items-center justify-center">
              <div>
                <GraduationCap className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h3 className="text-lg font-semibold text-gray-700 mb-2">还没有School</h3>
                <p className="text-gray-500">请先在AgentSchool页面创建School</p>
              </div>
            </div>
          ) : (
            <div className="h-full overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6">
                {schools.map((school) => {
                  const isCollapsed = collapsedSchools[school.id] !== false
                  const hasItems = (school.tools?.length || 0) > 0 || (school.skills?.length || 0) > 0 || (school.mcps?.length || 0) > 0

                  return (
                    <div
                      key={school.id}
                      onDragOver={handleDragOver}
                      onDrop={(e) => handleDropOnSchool(e, school)}
                      className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:border-primary-300 transition-colors"
                    >
                      {/* 卡片头部 - 可点击折叠 */}
                      <div
                        onClick={() => toggleSchoolCollapse(school.id)}
                        className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center space-x-3">
                          <button className="text-gray-400 hover:text-gray-600 transition-colors">
                            {isCollapsed ? (
                              <ChevronRight className="w-5 h-5" />
                            ) : (
                              <ChevronDown className="w-5 h-5" />
                            )}
                          </button>
                          <GraduationCap className="w-5 h-5 text-primary-600" />
                          <h3 className="font-semibold text-gray-800">{school.name}</h3>
                        </div>
                        <div className="flex items-center space-x-4 text-xs text-gray-500">
                          <span className="flex items-center space-x-1">
                            <Wrench className="w-3 h-3" />
                            <span>{school.tools?.length || 0}</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <Wand2 className="w-3 h-3" />
                            <span>{school.skills?.length || 0}</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <Cpu className="w-3 h-3" />
                            <span>{school.mcps?.length || 0}</span>
                          </span>
                        </div>
                      </div>

                      {/* 卡片内容 - 根据折叠状态显示 */}
                      {!isCollapsed && (
                        <div className="p-4 min-h-[200px]">
                          {!hasItems ? (
                            <div className="h-full flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
                              <p className="text-sm">拖拽工具、Skill 或 MCP 到这里</p>
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {/* Tools 列表 */}
                              {school.tools && school.tools.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-gray-500 mb-2 flex items-center space-x-1">
                                    <Wrench className="w-3 h-3" />
                                    <span>工具</span>
                                  </p>
                                  <div className="space-y-2">
                                    {school.tools.map((tool) => (
                                      <div
                                        key={tool.tool_name}
                                        draggable={false}
                                        className="p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all"
                                      >
                                        <div className="flex items-center justify-between">
                                          <div className="flex-1 min-w-0">
                                            <p className="font-medium text-sm">{tool.tool_name}</p>
                                            <p className="text-xs text-gray-500 truncate max-w-[200px]">
                                              {tool.tool_description}
                                            </p>
                                          </div>
                                          <button
                                            onClick={async (e) => {
                                              e.stopPropagation()
                                              const updatedTools = school.tools?.filter(t => t.tool_name !== tool.tool_name) || []
                                              await updateSchoolToolsState(school.id, updatedTools)
                                            }}
                                            className="p-1 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded transition-colors"
                                            title="移除工具"
                                          >
                                            <Trash2 className="w-4 h-4" />
                                          </button>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Skill 列表 */}
                              {school.skills && school.skills.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-gray-500 mb-2 flex items-center space-x-1">
                                    <Wand2 className="w-3 h-3" />
                                    <span>Skills</span>
                                  </p>
                                  <div className="space-y-2">
                                    {school.skills.map((skill) => {
                                      const skillInfo = skills.find(s => s.skill_id === skill.skill_id)
                                      return (
                                        <div
                                          key={skill.skill_id}
                                          draggable={false}
                                          className={`p-3 rounded-lg border hover:border-primary-300 hover:shadow-sm transition-all ${
                                            skill.enabled ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200 opacity-60'
                                          }`}
                                        >
                                          <div className="flex items-center justify-between">
                                            <div className="flex-1 min-w-0">
                                              <div className="flex items-center space-x-2">
                                                <Sparkles className="w-4 h-4 text-blue-600" />
                                                <p className="font-medium text-sm">{skillInfo?.name || skill.skill_id}</p>
                                              </div>
                                              <p className="text-xs text-gray-500 truncate max-w-[200px]">
                                                {skillInfo?.description || ''}
                                              </p>
                                            </div>
                                            <div className="flex items-center space-x-1">
                                              {!skill.enabled && (
                                                <button
                                                  onClick={async (e) => {
                                                    e.stopPropagation()
                                                    await toggleSkillEnabled(school.id, skill.skill_id, true)
                                                  }}
                                                  className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-100 rounded transition-colors"
                                                  title="启用 Skill"
                                                >
                                                  <div className="w-4 h-4 rounded-full border-2 border-gray-400" />
                                                </button>
                                              )}
                                              <button
                                                onClick={async (e) => {
                                                  e.stopPropagation()
                                                  const updatedSkills = school.skills?.filter(s => s.skill_id !== skill.skill_id) || []
                                                  await updateSchoolSkillsState(school.id, updatedSkills)
                                                }}
                                                className="p-1 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded transition-colors"
                                                title="移除 Skill"
                                              >
                                                <Trash2 className="w-4 h-4" />
                                              </button>
                                            </div>
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </div>
                              )}

                              {/* MCP 列表 */}
                              {school.mcps && school.mcps.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-gray-500 mb-2 flex items-center space-x-1">
                                    <Cpu className="w-3 h-3" />
                                    <span>MCPs</span>
                                  </p>
                                  <div className="space-y-2">
                                    {school.mcps.map((mcp) => (
                                      <div
                                        key={mcp.mcp_id}
                                        draggable={false}
                                        className={`p-3 rounded-lg border hover:border-primary-300 hover:shadow-sm transition-all ${
                                          mcp.enabled ? 'bg-yellow-50 border-yellow-200' : 'bg-gray-50 border-gray-200 opacity-60'
                                        }`}
                                      >
                                        <div className="flex items-center justify-between">
                                          <div className="flex-1 min-w-0">
                                            <div className="flex items-center space-x-2">
                                              <Zap className="w-4 h-4 text-yellow-600" />
                                              <p className="font-medium text-sm">{mcp.name}</p>
                                              <span className={`px-2 py-0.5 rounded-full text-xs ${
                                                mcp.mode === 'remote' ? 'text-purple-600 bg-purple-50' : 'text-green-600 bg-green-50'
                                              }`}>
                                                {mcp.mode === 'remote' ? 'Remote' : 'Stdio'}
                                              </span>
                                            </div>
                                            <p className="text-xs text-gray-500 truncate max-w-[200px]">
                                              {mcp.description || '无描述'}
                                            </p>
                                          </div>
                                          <button
                                            onClick={async (e) => {
                                              e.stopPropagation()
                                              const updatedMcps = school.mcps?.filter(m => m.mcp_id !== mcp.mcp_id) || []
                                              await updateSchoolMcpsState(school.id, updatedMcps)
                                            }}
                                            className="p-1 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded transition-colors"
                                            title="移除 MCP"
                                          >
                                            <Trash2 className="w-4 h-4" />
                                          </button>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* MCP 配置弹窗 */}
      <MCPConfigModal
        isOpen={showMcpConfigModal}
        onClose={() => setShowMcpConfigModal(false)}
        onSave={handleSaveMcp}
      />
    </div>
  )
}
