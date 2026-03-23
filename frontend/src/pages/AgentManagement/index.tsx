import { useEffect, useState } from 'react'
import { ArrowLeft, Plus, Bot, Sparkles, Settings, Loader2 } from 'lucide-react'
import { useModelStore } from '@/store/modelStore'
import { modelsApi } from '@/api/models'
import OllamaConfigWizard from './components/OllamaConfigWizard'
import AliyunConfigWizard from './components/AliyunConfigWizard'
import ProviderSelectDialog from './components/ProviderSelectDialog'
import AgentParamsEditor from './components/AgentParamsEditor'
import ModelList from './components/ModelList'

export default function AgentManagement() {
  const { 
    setModels,
    selectedModel
  } = useModelStore()

  useEffect(() => {
    const initData = async () => {
      try {
        const configs = await modelsApi.getConfigs()
        setModels(configs as any)
      } catch (error) {
        console.error('Failed to load data:', error)
      }
    }

    initData()
  }, [setModels])

  const handleBack = () => {
    const event = new CustomEvent('route-change', { 
      detail: { route: 'chat' as const } 
    })
    window.dispatchEvent(event)
  }

  const [showWizard, setShowWizard] = useState(false)
  const [showParamsEditor, setShowParamsEditor] = useState(false)
  const [showAliyunWizard, setShowAliyunWizard] = useState(false)
  const [showProviderSelect, setShowProviderSelect] = useState(false)

  const handleAddConfig = () => {
    setShowProviderSelect(true)
  }

  const handleCloseWizard = () => {
    setShowWizard(false)
  }

  const handleCloseAliyunWizard = () => {
    setShowAliyunWizard(false)
  }

  const handleCloseProviderSelect = () => {
    setShowProviderSelect(false)
  }

  const handleSelectAliyun = () => {
    setShowProviderSelect(false)
    setShowAliyunWizard(true)
  }

  const handleSelectOllama = () => {
    setShowProviderSelect(false)
    setShowWizard(true)
  }

  const handleOpenParamsEditor = () => {
    setShowParamsEditor(true)
  }

  const handleCloseParamsEditor = () => {
    setShowParamsEditor(false)
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <div className="h-14 bg-white flex items-center justify-between px-6">
        <div className="flex items-center space-x-2">
          <button
            onClick={handleBack}
            className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 shadow-soft hover:shadow-soft-hover transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-primary-600" />
            <h1 className="text-lg font-semibold text-gray-800">Agent配置</h1>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleAddConfig}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-primary text-white shadow-soft hover:shadow-soft-hover font-medium"
          >
            <Plus className="w-4 h-4" />
            <span>添加Agent</span>
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-80 bg-white flex flex-col">
          <div className="p-4">
            <h2 className="text-sm font-semibold text-gray-500 mb-3">已配置的Agent</h2>
          </div>
          <div className="flex-1 overflow-y-auto scrollbar-thin">
            <ModelList />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin p-6">
          {selectedModel ? (
            <div className="max-w-3xl mx-auto">
              <div className="bg-white shadow-sm p-6">
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">{selectedModel.name}</h2>
                    <p className="text-gray-600">
                      {selectedModel.provider === 'ollama' ? 'Ollama' :
                       selectedModel.provider === 'aliyun' ? '阿里云' :
                       selectedModel.provider === 'openai' ? 'OpenAI' :
                       selectedModel.provider === 'anthropic' ? 'Anthropic' : '自定义'} · {selectedModel.model}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    {selectedModel.is_testing && (
                      <span className="px-3 py-1 text-sm bg-red-100 text-red-800 flex items-center space-x-1">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>连接中...</span>
                      </span>
                    )}
                    {!selectedModel.is_testing && selectedModel.is_tested && selectedModel.test_result && (
                      <span className={`px-3 py-1 text-sm ${
                        selectedModel.test_result.success 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {selectedModel.test_result.success ? '连接正常' : '连接失败'}
                      </span>
                    )}
                    <button
                      onClick={handleOpenParamsEditor}
                      className="flex items-center space-x-2 px-4 py-2 bg-gradient-primary text-white shadow-soft hover:shadow-soft-hover font-medium"
                    >
                      <Settings className="w-4 h-4" />
                      <span>参数配置</span>
                    </button>
                  </div>
                </div>

                <div className="pt-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">配置详情</h3>
                  
                  <div className="space-y-4">
                    <div className="bg-gradient-primary p-4 shadow-soft">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">🦙</span>
                          <div>
                            <p className="font-medium text-gray-900">{selectedModel.name}</p>
                            <p className="text-sm text-gray-500">{selectedModel.model}</p>
                          </div>
                        </div>
                      </div>
                      {selectedModel.test_result && (
                        <div className="text-sm text-gray-600 mt-2">
                          <p>状态: {selectedModel.test_result.message}</p>
                          {selectedModel.test_result.latency && (
                            <p>响应延迟: {selectedModel.test_result.latency.toFixed(2)}秒</p>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">服务地址</p>
                        <p className="font-medium text-gray-900 text-sm break-all">{selectedModel.api_base}</p>
                      </div>
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">Temperature</p>
                        <p className="font-medium text-gray-900">{selectedModel.temperature}</p>
                      </div>
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">Max Tokens</p>
                        <p className="font-medium text-gray-900">{selectedModel.max_tokens}</p>
                      </div>
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">Top P</p>
                        <p className="font-medium text-gray-900">{selectedModel.top_p ?? 'N/A'}</p>
                      </div>
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">Top K</p>
                        <p className="font-medium text-gray-900">{selectedModel.top_k ?? 'N/A'}</p>
                      </div>
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">Repeat Penalty</p>
                        <p className="font-medium text-gray-900">{selectedModel.repeat_penalty ?? 'N/A'}</p>
                      </div>
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">Presence Penalty</p>
                        <p className="font-medium text-gray-900">{selectedModel.presence_penalty ?? 'N/A'}</p>
                      </div>
                      <div className="bg-gray-50 p-4 shadow-soft">
                        <p className="text-sm text-gray-500 mb-1">Thinking</p>
                        <p className="font-medium text-gray-900">{selectedModel.thinking ? '启用' : '禁用'}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="w-20 h-20 bg-gradient-primary flex items-center justify-center mb-4 rounded-full">
                <Bot className="w-10 h-10 text-white" />
              </div>
              <p className="text-lg font-medium mb-2">还没有配置Agent</p>
              <p className="text-sm mb-4">点击右上角"添加Agent"按钮开始配置</p>
              <button
                onClick={handleAddConfig}
                className="px-6 py-3 bg-gradient-primary text-white shadow-soft hover:shadow-soft-hover font-medium flex items-center space-x-2 rounded-2xl"
              >
                <Plus className="w-4 h-4" />
                <span>添加第一个Agent</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {showWizard && <OllamaConfigWizard onClose={handleCloseWizard} />}
      {showAliyunWizard && <AliyunConfigWizard onClose={handleCloseAliyunWizard} />}
      {showProviderSelect && (
        <ProviderSelectDialog
          onClose={handleCloseProviderSelect}
          onSelectAliyun={handleSelectAliyun}
          onSelectOllama={handleSelectOllama}
        />
      )}
      {showParamsEditor && <AgentParamsEditor onClose={handleCloseParamsEditor} />}
    </div>
  )
}
