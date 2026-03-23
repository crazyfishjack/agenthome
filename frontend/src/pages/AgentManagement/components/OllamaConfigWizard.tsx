import { useState } from 'react'
import { X, Search, Check, AlertCircle, Loader2, ArrowRight, Info, RefreshCw, Bot } from 'lucide-react'
import { useModelStore } from '@/store/modelStore'
import { modelsApi } from '@/api/models'
import type { OllamaSearchResult } from '@/types/model'

// 默认参数值
const DEFAULT_PARAMS = {
  max_tokens: 2048,
  temperature: 0.7,
  thinking: false,
  top_p: 0.9,
  top_k: 40,
  repeat_penalty: 1.1,
  presence_penalty: 0
}

interface OllamaConfigWizardProps {
  onClose: () => void
}

export default function OllamaConfigWizard({ onClose }: OllamaConfigWizardProps) {
  const { addModel, setModelTesting, setModelTestResult } = useModelStore()
  
  const [step, setStep] = useState<'welcome' | 'search' | 'select' | 'config' | 'success'>('welcome')
  const [searchResult, setSearchResult] = useState<OllamaSearchResult | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [modelName, setModelName] = useState('')
  const [apiBase, setApiBase] = useState('http://localhost:11434')
  const [isSearching, setIsSearching] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    setIsSearching(true)
    setError(null)
    try {
      const result = await modelsApi.searchOllama()
      setSearchResult(result as unknown as OllamaSearchResult)
      if ((result as unknown as OllamaSearchResult).found) {
        setApiBase((result as unknown as OllamaSearchResult).api_base || 'http://localhost:11434')
        setStep('select')
      } else {
        setError((result as unknown as OllamaSearchResult).message)
      }
    } catch (err: any) {
      setError(err.message || '搜索失败，请检查网络连接')
    } finally {
      setIsSearching(false)
    }
  }

  const handleModelSelect = (model: string) => {
    setSelectedModel(model)
    setModelName(model.split(':')[0])
    setStep('config')
  }

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      const config = await modelsApi.createConfig({
        name: modelName,
        provider: 'ollama',
        type: 'local',
        api_base: apiBase,
        model: selectedModel,
        ...DEFAULT_PARAMS
      })
      
      addModel(config as any)
      
      // 标记为测试中
      setModelTesting((config as any).id, true)
      
      // 测试连接
      const testResult = await modelsApi.testConnection((config as any).id)
      setModelTestResult((config as any).id, testResult as any)
      
      if ((testResult as any).success) {
        setStep('success')
      } else {
        setError('配置已保存，但连接测试失败，请检查Ollama服务')
      }
    } catch (err: any) {
      setError(err.message || '保存配置失败')
    } finally {
      setIsSaving(false)
    }
  }

  const handleRetry = () => {
    setStep('search')
    setSearchResult(null)
    setSelectedModel('')
    setError(null)
  }

  const renderWelcome = () => (
    <div className="space-y-6">
      <div className="text-center py-8">
        <div className="w-20 h-20 bg-gradient-primary mx-auto mb-6 flex items-center justify-center rounded-full">
          <Bot className="w-10 h-10 text-white" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-3">欢迎使用Agent配置</h2>
        <p className="text-gray-600 max-w-md mx-auto">
          我们将帮助您轻松配置本地Agent，只需几步即可开始使用
        </p>
      </div>

      <div className="bg-gradient-primary p-6 shadow-elegant">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center">
          <Info className="w-5 h-5 mr-2 text-white" />
          配置前准备
        </h3>
        <div className="space-y-3 text-sm text-gray-700">
          <div className="flex items-start">
            <span className="w-6 h-6 bg-white/20 flex items-center justify-center text-white font-bold mr-3 flex-shrink-0 mt-0.5">1</span>
            <p>确保已在电脑上安装并启动了Ollama</p>
          </div>
          <div className="flex items-start">
            <span className="w-6 h-6 bg-white/20 flex items-center justify-center text-white font-bold mr-3 flex-shrink-0 mt-0.5">2</span>
            <p>Ollama默认运行在 <code className="bg-white/20 px-2 py-0.5 text-white">http://localhost:11434</code></p>
          </div>
          <div className="flex items-start">
            <span className="w-6 h-6 bg-white/20 flex items-center justify-center text-white font-bold mr-3 flex-shrink-0 mt-0.5">3</span>
            <p>已下载至少一个Agent模型（如 llama3, mistral 等）</p>
          </div>
        </div>
      </div>

      <button
        onClick={() => setStep('search')}
        className="w-full py-4 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover font-semibold flex items-center justify-center space-x-2"
      >
        <span>开始配置</span>
        <ArrowRight className="w-5 h-5" />
      </button>
    </div>
  )

  const renderSearch = () => (
    <div className="space-y-6">
      <div className="text-center py-6">
        <div className="w-16 h-16 bg-gradient-primary mx-auto mb-4 flex items-center justify-center">
          <Search className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">搜索本地Ollama服务</h2>
        <p className="text-gray-600 text-sm">
          点击下方按钮，我们将自动搜索您电脑上运行的Ollama服务
        </p>
      </div>

      <div className="bg-info-50 p-5 shadow-elegant">
        <h3 className="font-medium text-info-900 mb-3 flex items-center text-sm">
          <Info className="w-4 h-4 mr-2" />
          搜索说明
        </h3>
        <ul className="text-sm text-info-800 space-y-2">
          <li>• 自动检测常见的Ollama地址</li>
          <li>• 获取已安装的Agent列表</li>
          <li>• 无需手动输入服务地址</li>
        </ul>
      </div>

      <button
        onClick={handleSearch}
        disabled={isSearching}
        className="w-full py-4 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover font-semibold flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSearching ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>正在搜索...</span>
          </>
        ) : (
          <>
            <Search className="w-5 h-5" />
            <span>一键搜索Ollama</span>
          </>
        )}
      </button>

      {error && (
        <div className="p-4 bg-danger-50 shadow-elegant flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-danger-800">搜索失败</p>
            <p className="text-sm text-danger-700 mt-1">{error}</p>
            <button
              onClick={handleRetry}
              className="mt-2 text-sm text-danger-700 hover:text-danger-900 flex items-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>重试</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )

  const renderSelect = () => (
    <div className="space-y-6">
      <div className="text-center py-4">
        <div className="w-16 h-16 bg-gradient-primary mx-auto mb-4 flex items-center justify-center">
          <Check className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">找到Ollama服务！</h2>
        <p className="text-gray-600 text-sm">
          服务地址：<code className="bg-gray-100 px-2 py-0.5 text-gray-800">{searchResult?.api_base}</code>
        </p>
      </div>

      <div className="bg-success-50 p-5 shadow-elegant">
        <h3 className="font-medium text-success-900 mb-3 text-sm">已找到 {searchResult?.models.length} 个Agent模型</h3>
        <p className="text-sm text-success-800">请选择一个Agent模型进行配置：</p>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {searchResult?.models.map((model) => (
          <button
            key={model}
            onClick={() => handleModelSelect(model)}
            className={`w-full text-left px-4 py-3 shadow-elegant hover:shadow-elegant-hover ${
              selectedModel === model
                ? 'bg-gradient-primary'
                : 'bg-white hover:bg-gray-100'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{model}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {model.includes('llama') ? 'Llama系列' :
                   model.includes('mistral') ? 'Mistral系列' :
                   model.includes('phi') ? 'Phi系列' :
                   '其他模型'}
                </p>
              </div>
              {selectedModel === model && (
                <div className="w-6 h-6 bg-success-600 flex items-center justify-center">
                  <Check className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          </button>
        ))}
      </div>

      <button
        onClick={handleRetry}
        className="w-full py-3 bg-gray-100 text-gray-700 shadow-elegant hover:shadow-elegant-hover font-medium flex items-center justify-center space-x-2"
      >
        <RefreshCw className="w-4 h-4" />
        <span>重新搜索</span>
      </button>
    </div>
  )

  const renderConfig = () => (
    <div className="space-y-6">
      <div className="text-center py-4">
        <div className="w-16 h-16 bg-gradient-primary mx-auto mb-4 flex items-center justify-center rounded-full">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">确认配置信息</h2>
        <p className="text-gray-600 text-sm">
          请确认以下信息，然后点击保存
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            配置名称 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            placeholder="例如：我的Llama3 Agent"
            className="w-full px-4 py-3 shadow-elegant focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">给这个配置起一个好记的名字</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            服务地址
          </label>
          <input
            type="text"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            className="w-full px-4 py-3 bg-gray-50 shadow-elegant focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">自动检测到的Ollama地址</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            选择的Agent模型
          </label>
          <div className="px-4 py-3 bg-gray-50 shadow-elegant">
            <p className="font-medium text-gray-900">{selectedModel}</p>
          </div>
        </div>
      </div>

      <div className="flex space-x-3">
        <button
          onClick={() => setStep('select')}
          className="flex-1 py-3 bg-gray-100 text-gray-700 shadow-elegant hover:shadow-elegant-hover font-medium"
        >
          上一步
        </button>
        <button
          onClick={handleSave}
          disabled={!modelName || isSaving}
          className="flex-1 py-3 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover font-semibold flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>保存中...</span>
            </>
          ) : (
            <>
              <Check className="w-4 h-4" />
              <span>保存配置</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-danger-50 shadow-elegant flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-danger-800">保存失败</p>
            <p className="text-sm text-danger-700 mt-1">{error}</p>
          </div>
        </div>
      )}
    </div>
  )

  const renderSuccess = () => (
    <div className="space-y-6 text-center py-8">
      <div className="w-20 h-20 bg-gradient-primary mx-auto mb-6 flex items-center justify-center rounded-full">
        <Check className="w-10 h-10 text-white" />
      </div>
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">配置成功！</h2>
        <p className="text-gray-600">
          Agent <span className="font-semibold text-gray-900">{modelName}</span> 已添加成功
        </p>
      </div>

      <div className="bg-success-50 p-5 shadow-elegant text-left">
        <h3 className="font-medium text-success-900 mb-3 text-sm">接下来您可以：</h3>
        <ul className="text-sm text-success-800 space-y-2">
          <li>• 在左侧列表中找到新添加的Agent</li>
          <li>• 点击Agent开始对话</li>
          <li>• 继续添加更多Agent</li>
        </ul>
      </div>

      <button
        onClick={onClose}
        className="w-full py-4 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover font-semibold"
      >
        开始使用
      </button>
    </div>
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Agent配置</h2>
            <p className="text-sm text-gray-500 mt-1">简单几步，轻松配置</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {step === 'welcome' && renderWelcome()}
          {step === 'search' && renderSearch()}
          {step === 'select' && renderSelect()}
          {step === 'config' && renderConfig()}
          {step === 'success' && renderSuccess()}
        </div>
      </div>
    </div>
  )
}
