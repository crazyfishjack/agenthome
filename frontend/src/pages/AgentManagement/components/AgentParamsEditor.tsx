import { useState } from 'react'
import { X, Save, RotateCcw, Info } from 'lucide-react'
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
  presence_penalty: 0,
  system_prompt: ''
}

interface AgentParamsEditorProps {
  onClose: () => void
}

export default function AgentParamsEditor({ onClose }: AgentParamsEditorProps) {
  const { selectedModel, updateModelConfig } = useModelStore()
  const [isSaving, setIsSaving] = useState(false)

  // 初始化参数值
  const [params, setParams] = useState({
    max_tokens: selectedModel?.max_tokens ?? DEFAULT_PARAMS.max_tokens,
    temperature: selectedModel?.temperature ?? DEFAULT_PARAMS.temperature,
    thinking: selectedModel?.thinking ?? DEFAULT_PARAMS.thinking,
    top_p: selectedModel?.top_p ?? DEFAULT_PARAMS.top_p,
    top_k: selectedModel?.top_k ?? DEFAULT_PARAMS.top_k,
    repeat_penalty: selectedModel?.repeat_penalty ?? DEFAULT_PARAMS.repeat_penalty,
    presence_penalty: selectedModel?.presence_penalty ?? DEFAULT_PARAMS.presence_penalty,
    system_prompt: selectedModel?.system_prompt ?? DEFAULT_PARAMS.system_prompt
  })

  const handleReset = () => {
    setParams(DEFAULT_PARAMS)
  }

  const validateNumber = (value: number, min: number, max: number) => {
    return Math.max(min, Math.min(max, value))
  }

  const handleInputChange = (field: string, value: any) => {
    setParams(prev => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    if (!selectedModel) return

    setIsSaving(true)
    try {
      await modelsApi.updateConfig(selectedModel.id, params)
      updateModelConfig(selectedModel.id, params)
      setTimeout(() => {
        onClose()
      }, 300)
    } catch (error) {
      console.error('Failed to update config:', error)
      alert('保存失败，请重试')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">参数配置</h2>
            <p className="text-sm text-gray-500 mt-1">
              配置 {selectedModel?.name} 的生成参数
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* System Prompt */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                System Prompt (系统提示词)
              </label>
              <span className={`text-sm font-medium ${
                params.system_prompt.length > 2000 ? 'text-danger-600' : 'text-primary-600'
              }`}>
                {params.system_prompt.length} / 2000
              </span>
            </div>
            <textarea
              rows={6}
              maxLength={2000}
              value={params.system_prompt}
              onChange={(e) => handleInputChange('system_prompt', e.target.value)}
              placeholder="输入系统提示词，定义Agent的角色和行为..."
              className={`w-full px-4 py-3 shadow-elegant focus:outline-none focus:ring-2 resize-none ${
                params.system_prompt.length > 2000
                  ? 'focus:ring-danger-500 border-danger-500'
                  : 'focus:ring-primary-500'
              }`}
            />
            <p className="text-xs text-gray-500 mt-2">
              系统提示词用于定义Agent的角色、行为和响应风格。最多2000字。
            </p>
            {params.system_prompt.length > 2000 && (
              <p className="text-xs text-danger-600 mt-1">
                已超过字数限制，请精简内容
              </p>
            )}
          </div>

          {/* Max Tokens */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Max Tokens (最大令牌数)
              </label>
              <span className="text-sm text-primary-600 font-medium">
                {params.max_tokens}
              </span>
            </div>
            <input
              type="number"
              min="1"
              max="128000"
              value={params.max_tokens}
              onChange={(e) => handleInputChange('max_tokens', validateNumber(parseInt(e.target.value) || 1, 1, 128000))}
              className="w-full px-4 py-3 shadow-elegant focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>推荐: 2048</span>
              <span>128000</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              控制模型生成的最大令牌数。1个令牌约等于0.75个英文单词或0.5个中文字符。
            </p>
          </div>

          {/* Temperature */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Temperature (温度)
              </label>
              <span className="text-sm text-primary-600 font-medium">
                {params.temperature.toFixed(1)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={params.temperature}
              onChange={(e) => handleInputChange('temperature', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 appearance-none cursor-pointer accent-primary-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0.0 (精确)</span>
              <span>1.0 (平衡)</span>
              <span>2.0 (创意)</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              控制输出的随机性。较低的值使输出更确定，较高的值使输出更随机和创意。
            </p>
          </div>

          {/* Thinking */}
          <div className="p-4 bg-gradient-primary shadow-elegant">
            <div className="flex items-start space-x-3">
              <input
                type="checkbox"
                id="thinking"
                checked={params.thinking}
                onChange={(e) => handleInputChange('thinking', e.target.checked)}
                className="w-5 h-5 mt-0.5 text-primary-600 focus:ring-primary-500 rounded"
              />
              <div className="flex-1">
                <label htmlFor="thinking" className="block text-sm font-medium text-gray-900 cursor-pointer">
                  Thinking (深度思考)
                </label>
                <p className="text-xs text-gray-700 mt-1">
                  启用后，Agent会在回答前进行深度思考，提供更详细和准确的分析。适用于复杂问题和需要推理的场景。
                </p>
              </div>
            </div>
          </div>

          {/* Top P */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Top P (核采样)
              </label>
              <span className="text-sm text-primary-600 font-medium">
                {params.top_p.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={params.top_p}
              onChange={(e) => handleInputChange('top_p', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 appearance-none cursor-pointer accent-primary-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0.0 (保守)</span>
              <span>0.5 (平衡)</span>
              <span>1.0 (多样)</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              控制输出的多样性。值越小，输出越集中；值越大，输出越多样化。通常与Temperature二选一使用。
            </p>
          </div>

          {/* Top K */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Top K (采样数)
              </label>
              <span className="text-sm text-primary-600 font-medium">
                {params.top_k}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="100"
              step="1"
              value={params.top_k}
              onChange={(e) => handleInputChange('top_k', parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 appearance-none cursor-pointer accent-primary-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>推荐: 40</span>
              <span>100</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              控制输出的范围。只从概率最高的K个令牌中选择。值越小，输出越确定；值越大，输出越多样。
            </p>
          </div>

          {/* Repeat Penalty */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Repeat Penalty (重复惩罚)
              </label>
              <span className="text-sm text-primary-600 font-medium">
                {params.repeat_penalty.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={params.repeat_penalty}
              onChange={(e) => handleInputChange('repeat_penalty', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 appearance-none cursor-pointer accent-primary-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0.0 (无惩罚)</span>
              <span>1.1 (推荐)</span>
              <span>2.0 (强惩罚)</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              控制重复内容的惩罚力度。值越大，模型越倾向于避免重复相同的内容。
            </p>
          </div>

          {/* Presence Penalty */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Presence Penalty (存在惩罚)
              </label>
              <span className="text-sm text-primary-600 font-medium">
                {params.presence_penalty.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={params.presence_penalty}
              onChange={(e) => handleInputChange('presence_penalty', parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 appearance-none cursor-pointer accent-primary-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0.0 (无惩罚)</span>
              <span>1.0 (平衡)</span>
              <span>2.0 (强惩罚)</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              控制新话题的鼓励程度。值越大，模型越倾向于引入新话题和内容，避免停留在已讨论的话题上。
            </p>
          </div>

          {/* 参数说明卡片 */}
          <div className="p-4 bg-gray-50 shadow-elegant">
            <h4 className="font-medium text-gray-900 mb-3 flex items-center">
              <Info className="w-4 h-4 mr-2 text-primary-600" />
              参数配置建议
            </h4>
            <div className="space-y-2 text-sm text-gray-600">
              <p><strong>精确输出：</strong> Temperature 0.0-0.3, Top P 0.5-0.7</p>
              <p><strong>平衡输出：</strong> Temperature 0.4-0.7, Top P 0.8-0.9 (推荐)</p>
              <p><strong>创意输出：</strong> Temperature 0.8-2.0, Top P 0.9-1.0</p>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t">
          <button
            onClick={handleReset}
            className="flex items-center space-x-1 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-all"
            title="恢复默认值"
          >
            <RotateCcw className="w-4 h-4" />
            <span>重置</span>
          </button>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-gray-100 text-gray-700 shadow-elegant hover:shadow-elegant-hover font-medium"
            >
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-6 py-2 bg-gradient-primary text-white shadow-elegant hover:shadow-elegant-hover font-medium flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? (
                <>
                  <span>保存中...</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>保存配置</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
