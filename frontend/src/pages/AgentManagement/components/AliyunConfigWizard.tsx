import { useState } from 'react'
import { X, Check, AlertCircle, Loader2, Cloud, Info } from 'lucide-react'
import { useModelStore } from '@/store/modelStore'
import { modelsApi } from '@/api/models'

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

interface AliyunConfigWizardProps {
  onClose: () => void
}

export default function AliyunConfigWizard({ onClose }: AliyunConfigWizardProps) {
  const { addModel, setModelTesting, setModelTestResult } = useModelStore()

  const [step, setStep] = useState<'form' | 'success'>('form')
  const [formData, setFormData] = useState({
    apiEndpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    apiKey: '',
    modelName: 'qwen-plus',
    agentName: ''
  })
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleInputChange = (field: keyof typeof formData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    // 验证必填字段
    if (!formData.apiEndpoint || !formData.apiKey || !formData.modelName || !formData.agentName) {
      setError('请填写所有必填字段')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      const config = await modelsApi.createConfig({
        name: formData.agentName,
        provider: 'aliyun',
        type: 'api',
        api_base: formData.apiEndpoint,
        api_key: formData.apiKey,
        model: formData.modelName,
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
        setError('配置已保存，但连接测试失败，请检查配置信息')
      }
    } catch (err: any) {
      setError(err.message || '保存配置失败')
    } finally {
      setIsSaving(false)
    }
  }

  const renderForm = () => (
    <div className="space-y-6">
      <div className="text-center py-4">
        <div className="w-16 h-16 bg-gradient-primary mx-auto mb-4 flex items-center justify-center rounded-full">
          <Cloud className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">从阿里云配置 Agent</h2>
        <p className="text-gray-600 text-sm">
          填写阿里云通义千问的配置信息
        </p>
      </div>

      <div className="bg-info-50 p-5 shadow-elegant">
        <h3 className="font-medium text-info-900 mb-3 flex items-center text-sm">
          <Info className="w-4 h-4 mr-2" />
          配置说明
        </h3>
        <ul className="text-sm text-info-800 space-y-2">
          <li>• API 端点：默认为阿里云兼容模式端点</li>
          <li>• API Key：从阿里云控制台获取</li>
          <li>• 模型名称：如 qwen-turbo, qwen-plus, qwen-max 等</li>
          <li>• Agent 名称：为这个配置起一个好记的名字</li>
        </ul>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            API 端点 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.apiEndpoint}
            onChange={(e) => handleInputChange('apiEndpoint', e.target.value)}
            placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
            className="w-full px-4 py-3 shadow-elegant focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">阿里云通义千问 API 端点地址</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            API Key <span className="text-red-500">*</span>
          </label>
          <input
            type="password"
            value={formData.apiKey}
            onChange={(e) => handleInputChange('apiKey', e.target.value)}
            placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
            className="w-full px-4 py-3 shadow-elegant focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">从阿里云控制台获取的 API Key</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            模型名称 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.modelName}
            onChange={(e) => handleInputChange('modelName', e.target.value)}
            placeholder="例如：qwen-plus, qwen-max, qwen-turbo"
            className="w-full px-4 py-3 shadow-elegant focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">输入通义千问模型名称，如 qwen-turbo, qwen-plus, qwen-max 等</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Agent 名称（配置名称） <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.agentName}
            onChange={(e) => handleInputChange('agentName', e.target.value)}
            placeholder="例如：我的通义千问 Agent"
            className="w-full px-4 py-3 shadow-elegant focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="text-xs text-gray-500 mt-1">给这个配置起一个好记的名字</p>
        </div>
      </div>

      <div className="flex space-x-3">
        <button
          onClick={onClose}
          className="flex-1 py-3 bg-gray-100 text-gray-700 shadow-elegant hover:shadow-elegant-hover font-medium"
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
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
          Agent <span className="font-semibold text-gray-900">{formData.agentName}</span> 已添加成功
        </p>
      </div>

      <div className="bg-success-50 p-5 shadow-elegant text-left">
        <h3 className="font-medium text-success-900 mb-3 text-sm">接下来您可以：</h3>
        <ul className="text-sm text-success-800 space-y-2">
          <li>• 在左侧列表中找到新添加的 Agent</li>
          <li>• 点击 Agent 开始对话</li>
          <li>• 配置 School、Tools 和 Skills</li>
          <li>• 继续添加更多 Agent</li>
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
            <h2 className="text-xl font-bold text-gray-900">阿里云配置</h2>
            <p className="text-sm text-gray-500 mt-1">快速配置通义千问 Agent</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {step === 'form' && renderForm()}
          {step === 'success' && renderSuccess()}
        </div>
      </div>
    </div>
  )
}
