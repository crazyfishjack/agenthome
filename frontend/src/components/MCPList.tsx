import React, { useState } from 'react'
import { Zap, ChevronDown, ChevronRight, Trash2 } from 'lucide-react'
import type { MCPConfig } from '@/types/school'

interface MCPListProps {
  mcps: MCPConfig[]
  onMcpDragStart: (e: React.DragEvent, mcp: MCPConfig) => void
  onMcpDragEnd: () => void
  onMcpDelete?: (mcpId: string) => void
}

export default function MCPList({ mcps, onMcpDragStart, onMcpDragEnd, onMcpDelete }: MCPListProps) {
  const [expandedMcps, setExpandedMcps] = useState<Set<string>>(new Set())
  const [deleteConfirmMcpId, setDeleteConfirmMcpId] = useState<string | null>(null)

  const toggleMcpExpansion = (mcpId: string) => {
    const newExpanded = new Set(expandedMcps)
    if (newExpanded.has(mcpId)) {
      newExpanded.delete(mcpId)
    } else {
      newExpanded.add(mcpId)
    }
    setExpandedMcps(newExpanded)
  }

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case 'remote':
        return 'Remote'
      case 'stdio':
        return 'Stdio'
      default:
        return mode
    }
  }

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'remote':
        return 'text-purple-600 bg-purple-50'
      case 'stdio':
        return 'text-green-600 bg-green-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const handleDeleteClick = (e: React.MouseEvent, mcpId: string) => {
    e.stopPropagation()
    setDeleteConfirmMcpId(mcpId)
  }

  const handleConfirmDelete = (e: React.MouseEvent, mcpId: string) => {
    e.stopPropagation()
    setDeleteConfirmMcpId(null)
    if (onMcpDelete) {
      onMcpDelete(mcpId)
    }
  }

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setDeleteConfirmMcpId(null)
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 bg-yellow-50 border-b border-yellow-200">
        <div className="flex items-center space-x-2">
          <Zap className="w-5 h-5 text-yellow-600" />
          <h2 className="font-semibold text-gray-800">MCP 列表</h2>
        </div>
        <p className="text-xs text-gray-500 mt-1">拖拽 MCP 到 School 中</p>
      </div>
      <div className="p-4 space-y-2 max-h-[600px] overflow-y-auto">
        {mcps.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Zap className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">暂无 MCP 配置</p>
          </div>
        ) : (
          mcps.map((mcp) => {
            const isDeleteConfirm = deleteConfirmMcpId === mcp.mcp_id
            return (
              <div
                key={mcp.mcp_id}
                draggable={!isDeleteConfirm}
                onDragStart={(e) => !isDeleteConfirm && onMcpDragStart(e, mcp)}
                onDragEnd={onMcpDragEnd}
                className={`relative p-3 rounded-lg border bg-yellow-50 border-yellow-200 hover:border-yellow-300 hover:shadow-sm transition-all ${isDeleteConfirm ? 'cursor-default' : 'cursor-move'}`}
              >
                <div className="flex items-center space-x-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <Zap className="w-4 h-4 text-yellow-600" />
                      <p className="font-medium text-sm truncate">{mcp.name}</p>
                      <span className={`px-2 py-0.5 rounded-full text-xs ${getModeColor(mcp.mode)}`}>
                        {getModeLabel(mcp.mode)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 truncate">{mcp.description || '无描述'}</p>
                  </div>
                  {!isDeleteConfirm && (
                    <>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleMcpExpansion(mcp.mcp_id)
                        }}
                        className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                      >
                        {expandedMcps.has(mcp.mcp_id) ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>
                      {onMcpDelete && (
                        <button
                          onClick={(e) => handleDeleteClick(e, mcp.mcp_id)}
                          className="p-1 text-gray-400 hover:text-danger-600 hover:bg-gray-100 rounded transition-colors"
                          title="删除 MCP"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </>
                  )}
                </div>
                {expandedMcps.has(mcp.mcp_id) && !isDeleteConfirm && (
                  <div className="mt-2 text-xs text-gray-600 bg-white p-2 rounded border border-yellow-100">
                    <p className="font-medium mb-1">模式：{getModeLabel(mcp.mode)}</p>
                    <p className="font-medium mb-1">配置：</p>
                    <pre className="bg-gray-50 p-2 rounded overflow-x-auto text-xs">
                      {JSON.stringify(mcp.config, null, 2)}
                    </pre>
                  </div>
                )}
                {/* 删除确认对话框 */}
                {isDeleteConfirm && (
                  <div
                    className="absolute inset-0 bg-white/95 backdrop-blur-sm z-10 flex items-center justify-center p-4 rounded-lg"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="text-center">
                      <p className="text-sm text-gray-700 mb-3">确定要删除这个 MCP 吗？</p>
                      <p className="text-xs text-gray-500 mb-3">删除后，所有使用此 MCP 的 School 和 Agent 都会移除相关配置。</p>
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={handleCancelDelete}
                          className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                        >
                          取消
                        </button>
                        <button
                          onClick={(e) => handleConfirmDelete(e, mcp.mcp_id)}
                          className="px-3 py-1.5 text-sm text-white bg-danger-500 hover:bg-danger-600 rounded-full transition-colors"
                        >
                          确定
                        </button>
                      </div>
                    </div>
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
