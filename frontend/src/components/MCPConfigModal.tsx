import React, { useState } from 'react'
import { X, Plus, CheckCircle2, Loader2 } from 'lucide-react'

interface MCPConfigModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: {
    name: string
    description?: string
    mode: 'remote' | 'stdio'
    config: any
  }) => Promise<void>
}

export default function MCPConfigModal({ isOpen, onClose, onSave }: MCPConfigModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [mode, setMode] = useState<'remote' | 'stdio'>('remote')
  const [, setConfig] = useState<any>({})
  const [configJson, setConfigJson] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testSuccess, setTestSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 根据模式设置默认配置
  React.useEffect(() => {
    if (mode === 'remote') {
      const defaultConfig = {
        type: 'streamable_http',
        url: ''
      }
      setConfig(defaultConfig)
      setConfigJson(JSON.stringify(defaultConfig, null, 2))
    } else {
      const defaultConfig = {
        command: '',
        args: []
      }
      setConfig(defaultConfig)
      setConfigJson(JSON.stringify(defaultConfig, null, 2))
    }
  }, [mode])

  // 处理配置 JSON 变化
  const handleConfigJsonChange = (value: string) => {
    setConfigJson(value)
    try {
      const parsed = JSON.parse(value)
      setConfig(parsed)
      setError(null)
    } catch (e) {
      setError('JSON 格式错误')
    }
  }

  // 保存配置
  const handleSave = async () => {
    if (!name.trim()) {
      setError('请输入 MCP 名称')
      return
    }

    if (!configJson.trim()) {
      setError('请输入 MCP 配置')
      return
    }

    try {
      const parsedConfig = JSON.parse(configJson)
      setSaving(true)
      setTesting(true)
      setError(null)
      setTestSuccess(false)

      await onSave({
        name: name.trim(),
        description: description.trim() || undefined,
        mode,
        config: parsedConfig
      })

      // 测试成功
      setTesting(false)
      setTestSuccess(true)

      // 延迟关闭窗口，让用户看到测试成功的提示
      setTimeout(() => {
        // 重置表单
        setName('')
        setDescription('')
        setMode('remote')
        setConfigJson('')
        setConfig({})
        setTestSuccess(false)
        onClose()
      }, 1000)
    } catch (e) {
      setTesting(false)
      setError('保存失败：' + (e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* 标题栏 */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">配置 MCP</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* 提示信息 */}
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              MCP（Model Context Protocol）允许 Agent 调用外部工具和服务。
              请根据您的 MCP 服务器类型选择相应的配置模式。
            </p>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {/* 表单 */}
          <div className="space-y-4">
            {/* MCP 名称 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                MCP 名称 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：My MCP Server"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            {/* MCP 描述 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                MCP 描述
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="简要描述 MCP 的功能和用途"
                rows={2}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            {/* MCP 模式 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                MCP 模式 <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  type="button"
                  onClick={() => setMode('remote')}
                  className={`p-4 border-2 rounded-lg transition-all ${
                    mode === 'remote'
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="text-center">
                    <div className="font-semibold text-gray-800 mb-1">Remote</div>
                    <div className="text-xs text-gray-600">通过 HTTP 连接远程 MCP 服务器</div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setMode('stdio')}
                  className={`p-4 border-2 rounded-lg transition-all ${
                    mode === 'stdio'
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="text-center">
                    <div className="font-semibold text-gray-800 mb-1">Stdio</div>
                    <div className="text-xs text-gray-600">通过标准输入输出连接本地进程</div>
                  </div>
                </button>
              </div>
            </div>

            {/* MCP 配置 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                MCP 配置 (JSON) <span className="text-red-500">*</span>
              </label>
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                {mode === 'remote' && (
                  <div className="mb-3 text-sm text-gray-600">
                    <p className="font-medium mb-1">Remote 模式配置说明：</p>
                    <ul className="list-disc list-inside space-y-1 text-xs">
                      <li><code>type</code>: 固定为 "streamable_http"</li>
                      <li><code>url</code>: MCP 服务器的 HTTP 地址</li>
                    </ul>
                  </div>
                )}
                {mode === 'stdio' && (
                  <div className="mb-3 text-sm text-gray-600">
                    <p className="font-medium mb-1">Stdio 模式配置说明：</p>
                    <ul className="list-disc list-inside space-y-1 text-xs">
                      <li><code>command</code>: 执行命令（如 "node", "python"）</li>
                      <li><code>args</code>: 命令参数数组</li>
                    </ul>
                  </div>
                )}
                <textarea
                  value={configJson}
                  onChange={(e) => handleConfigJsonChange(e.target.value)}
                  placeholder={mode === 'remote' ? '{\n  "type": "streamable_http",\n  "url": "http://localhost:3000/mcp"\n}' : '{\n  "command": "node",\n  "args": ["server.js"]\n}'}
                  rows={8}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm"
                />
              </div>
            </div>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="px-6 py-4 border-t border-gray-200">
          {/* 测试状态提示 */}
          {testing && (
            <div className="mb-3 flex items-center justify-center space-x-2 text-blue-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">正在测试连接...</span>
            </div>
          )}
          {testSuccess && (
            <div className="mb-3 flex items-center justify-center space-x-2 text-green-600">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-sm">测试可连接</span>
            </div>
          )}
          
          <div className="flex justify-end space-x-3">
            <button
              onClick={onClose}
              disabled={saving || testing}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={saving || testing}
              className="px-4 py-2 bg-gradient-primary text-white rounded-lg hover:shadow-elegant-hover transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>保存中...</span>
                </>
              ) : testing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>测试中...</span>
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  <span>添加 MCP</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
