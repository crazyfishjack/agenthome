import { X, Cloud, Bot, ArrowRight } from 'lucide-react'

interface ProviderSelectDialogProps {
  onClose: () => void
  onSelectAliyun: () => void
  onSelectOllama: () => void
}

export default function ProviderSelectDialog({ onClose, onSelectAliyun, onSelectOllama }: ProviderSelectDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white shadow-xl max-w-2xl w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">添加 Agent</h2>
            <p className="text-sm text-gray-500 mt-1">选择配置方式</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 shadow-elegant hover:shadow-elegant-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 阿里云配置选项 */}
            <button
              onClick={onSelectAliyun}
              className="group p-6 bg-gradient-primary shadow-elegant hover:shadow-elegant-hover transition-all duration-200 text-left"
            >
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-white/20 flex items-center justify-center rounded-lg flex-shrink-0">
                  <Cloud className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-white mb-2">从阿里云配置</h3>
                  <p className="text-sm text-white/80 mb-3">
                    使用阿里云通义千问 API
                  </p>
                  <ul className="text-xs text-white/70 space-y-1">
                    <li>• 支持多种模型选择</li>
                    <li>• 云端服务，无需本地部署</li>
                    <li>• 高性能，稳定可靠</li>
                  </ul>
                </div>
                <ArrowRight className="w-5 h-5 text-white/60 group-hover:text-white group-hover:translate-x-1 transition-all" />
              </div>
            </button>

            {/* Ollama 配置选项 */}
            <button
              onClick={onSelectOllama}
              className="group p-6 bg-white border-2 border-gray-200 hover:border-primary-500 shadow-elegant hover:shadow-elegant-hover transition-all duration-200 text-left"
            >
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-gradient-primary flex items-center justify-center rounded-lg flex-shrink-0">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-gray-900 mb-2">从 Ollama 配置</h3>
                  <p className="text-sm text-gray-600 mb-3">
                    使用本地 Ollama 服务
                  </p>
                  <ul className="text-xs text-gray-500 space-y-1">
                    <li>• 本地运行，数据隐私安全</li>
                    <li>• 支持多种开源模型</li>
                    <li>• 免费使用，无 API 费用</li>
                  </ul>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-primary-600 group-hover:translate-x-1 transition-all" />
              </div>
            </button>
          </div>

          <div className="mt-6 p-4 bg-info-50 shadow-elegant">
            <p className="text-sm text-info-800">
              <strong>提示：</strong>如果您是第一次使用，建议从 Ollama 开始，它完全免费且易于配置。如果您需要更强的性能和更丰富的功能，可以选择阿里云。
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
