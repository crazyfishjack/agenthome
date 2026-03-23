import { useState } from 'react'
import { useModelStore } from '@/store/modelStore'
import { Bot, Trash2, Loader2 } from 'lucide-react'
import { modelsApi } from '@/api/models'

export default function ModelList() {
  const { models, selectedModel, setSelectedModel, removeModel } = useModelStore()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [modelToDelete, setModelToDelete] = useState<{ id: string; name: string } | null>(null)

  const getProviderIcon = (provider: string) => {
    const icons: Record<string, string> = {
      openai: '🤖',
      anthropic: '🧠',
      ollama: '🦙',
      aliyun: '☁️',
      custom: '⚙️'
    }
    return icons[provider] || '📦'
  }

  const getProviderName = (provider: string) => {
    const names: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      ollama: 'Ollama',
      aliyun: '阿里云',
      custom: 'Custom'
    }
    return names[provider] || provider
  }

  const handleDeleteClick = (e: React.MouseEvent, modelId: string, modelName: string) => {
    e.stopPropagation()
    setModelToDelete({ id: modelId, name: modelName })
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!modelToDelete) return

    try {
      await modelsApi.deleteConfig(modelToDelete.id)
      removeModel(modelToDelete.id)
    } catch (error) {
      console.error('Failed to delete model config:', error)
      alert('删除失败，请重试')
    } finally {
      setShowDeleteConfirm(false)
      setModelToDelete(null)
    }
  }

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDeleteConfirm(false)
    setModelToDelete(null)
  }

  return (
    <div className="space-y-2 p-4">
      {models.map((model) => (
        <div
          key={model.id}
          className={`relative group`}
        >
          <button
            onClick={() => setSelectedModel(model)}
            className={`w-full text-left px-4 py-3 transition-colors shadow-elegant hover:shadow-elegant-hover ${
              selectedModel?.id === model.id
                ? 'bg-gradient-primary text-primary-800'
                : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
            }`}
          >
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-100 flex items-center justify-center flex-shrink-0 text-lg rounded-full">
                {getProviderIcon(model.provider)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{model.name}</p>
                <p className="text-xs text-gray-500 truncate">
                  {getProviderName(model.provider)} · {model.model}
                </p>
                {model.is_testing && (
                  <div className="flex items-center space-x-1 mt-1">
                    <Loader2 className="w-3 h-3 text-danger-500 animate-spin" />
                    <p className="text-xs text-danger-500">连接中...</p>
                  </div>
                )}
                {!model.is_testing && model.is_tested && (
                  <div className="flex items-center space-x-1 mt-1">
                    <div className={`w-2 h-2 ${model.test_result?.success ? 'bg-success-500' : 'bg-danger-500'} rounded-full`} />
                    <p className="text-xs text-gray-400">
                      {model.test_result?.success ? '已测试' : '测试失败'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </button>
          <button
            onClick={(e) => handleDeleteClick(e, model.id, model.name)}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-400 hover:text-danger-600 hover:bg-danger-50 opacity-0 group-hover:opacity-100 transition-all"
            title="删除Agent配置"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          {/* 删除确认对话框 */}
          {showDeleteConfirm && modelToDelete?.id === model.id && (
            <div
              className="absolute inset-0 bg-white/95 backdrop-blur-sm z-10 flex items-center justify-center p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-center">
                <p className="text-sm text-gray-700 mb-3">确定要删除Agent配置【{modelToDelete.name}】吗？</p>
                <div className="flex items-center justify-center gap-2">
                  <button
                    onClick={handleCancelDelete}
                    className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleConfirmDelete}
                    className="px-3 py-1.5 text-sm text-white bg-danger-500 hover:bg-danger-600 rounded-full transition-colors"
                  >
                    确定
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
      {models.length === 0 && (
        <div className="text-center py-8 text-gray-400">
          <Bot className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm">暂无配置</p>
          <p className="text-xs">点击上方按钮添加配置</p>
        </div>
      )}
    </div>
  )
}
