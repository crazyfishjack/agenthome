import React, { useState } from 'react'
import { Wrench, ChevronDown, ChevronRight } from 'lucide-react'
import type { ToolConfig } from '@/store/toolStore'

interface ToolListProps {
  tools: ToolConfig[]
  onToolDragStart: (e: React.DragEvent, tool: ToolConfig) => void
  onToolDragEnd: () => void
}

export default function ToolList({ tools, onToolDragStart, onToolDragEnd }: ToolListProps) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set())

  const toggleToolExpansion = (toolName: string) => {
    const newExpanded = new Set(expandedTools)
    if (newExpanded.has(toolName)) {
      newExpanded.delete(toolName)
    } else {
      newExpanded.add(toolName)
    }
    setExpandedTools(newExpanded)
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <Wrench className="w-5 h-5 text-primary-600" />
          <h2 className="font-semibold text-gray-800">工具列表</h2>
        </div>
        <p className="text-xs text-gray-500 mt-1">拖拽工具到School中</p>
      </div>
      <div className="p-4 space-y-2 max-h-[600px] overflow-y-auto">
        {tools.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Wrench className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">暂无工具配置</p>
          </div>
        ) : (
          tools.map((tool) => {
            return (
              <div
                key={tool.tool_name}
                draggable
                onDragStart={(e) => onToolDragStart(e, tool)}
                onDragEnd={onToolDragEnd}
                className="p-3 rounded-lg border bg-white border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all cursor-move"
              >
                <div className="flex items-center space-x-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{tool.tool_name}</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleToolExpansion(tool.tool_name)
                    }}
                    className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                  >
                    {expandedTools.has(tool.tool_name) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                </div>
                {expandedTools.has(tool.tool_name) && (
                  <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
                    <p className="font-medium mb-1">参数要求：</p>
                    <p className="whitespace-pre-wrap">{tool.parameter_requirements}</p>
                    <p className="font-medium mt-2 mb-1">格式要求：</p>
                    <p className="whitespace-pre-wrap">{tool.format_requirements}</p>
                    {tool.examples.length > 0 && (
                      <>
                        <p className="font-medium mt-2 mb-1">示例：</p>
                        <ul className="list-disc list-inside space-y-1">
                          {tool.examples.map((example, idx) => (
                            <li key={idx} className="text-gray-700">{example}</li>
                          ))}
                        </ul>
                      </>
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
