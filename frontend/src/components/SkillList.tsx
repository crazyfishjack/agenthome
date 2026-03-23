import React, { useState } from 'react'
import { Sparkles, ChevronDown, ChevronRight } from 'lucide-react'

interface Skill {
  skill_id: string
  name: string
  description: string
  version: string
  author?: string
  tags?: string[]
}

interface SkillListProps {
  skills: Skill[]
  onSkillDragStart: (e: React.DragEvent, skill: Skill) => void
  onSkillDragEnd: () => void
}

export default function SkillList({ skills, onSkillDragStart, onSkillDragEnd }: SkillListProps) {
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set())

  const toggleSkillExpansion = (skillId: string) => {
    const newExpanded = new Set(expandedSkills)
    if (newExpanded.has(skillId)) {
      newExpanded.delete(skillId)
    } else {
      newExpanded.add(skillId)
    }
    setExpandedSkills(newExpanded)
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 bg-blue-50 border-b border-blue-200">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-blue-600" />
          <h2 className="font-semibold text-gray-800">Skill 列表</h2>
        </div>
        <p className="text-xs text-gray-500 mt-1">拖拽 Skill 到 School 中</p>
      </div>
      <div className="p-4 space-y-2 max-h-[600px] overflow-y-auto">
        {skills.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Sparkles className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">暂无 Skill 配置</p>
          </div>
        ) : (
          skills.map((skill) => {
            return (
              <div
                key={skill.skill_id}
                draggable
                onDragStart={(e) => onSkillDragStart(e, skill)}
                onDragEnd={onSkillDragEnd}
                className="p-3 rounded-lg border bg-blue-50 border-blue-200 hover:border-blue-300 hover:shadow-sm transition-all cursor-move"
              >
                <div className="flex items-center space-x-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <Sparkles className="w-4 h-4 text-blue-600" />
                      <p className="font-medium text-sm truncate">{skill.name}</p>
                    </div>
                    <p className="text-xs text-gray-500 truncate">{skill.description}</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleSkillExpansion(skill.skill_id)
                    }}
                    className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                  >
                    {expandedSkills.has(skill.skill_id) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                </div>
                {expandedSkills.has(skill.skill_id) && (
                  <div className="mt-2 text-xs text-gray-600 bg-white p-2 rounded border border-blue-100">
                    <p className="font-medium mb-1">版本：{skill.version}</p>
                    {skill.author && <p className="mb-1">作者：{skill.author}</p>}
                    {skill.tags && skill.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {skill.tags.map((tag, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
