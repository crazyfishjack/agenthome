interface TypingIndicatorProps {
  agentName?: string
}

export default function TypingIndicator({ agentName }: TypingIndicatorProps) {
  return (
    <div className="flex items-start space-x-3">
      {/* Agent Avatar */}
      <div className="w-8 h-8 bg-gradient-primary flex items-center justify-center text-white font-medium text-sm flex-shrink-0 rounded-full">
        {agentName ? agentName.charAt(0).toUpperCase() : 'A'}
      </div>

      {/* Typing Animation */}
      <div className="bg-gray-100 px-4 py-3 shadow-elegant rounded-2xl">
        <div className="flex space-x-2">
          <div className="w-2 h-2 bg-gray-400 animate-bounce rounded-full"></div>
          <div className="w-2 h-2 bg-gray-400 animate-bounce delay-100 rounded-full"></div>
          <div className="w-2 h-2 bg-gray-400 animate-bounce delay-200 rounded-full"></div>
        </div>
      </div>
    </div>
  )
}
