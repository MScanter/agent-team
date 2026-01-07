import { useEffect, useRef } from 'react'
import { Loader2, User, Bot } from 'lucide-react'
import type { ExecutionMessage } from '@/types'

interface Props {
  messages: ExecutionMessage[]
  status: 'idle' | 'connecting' | 'connected' | 'completed' | 'error'
  error?: string | null
}

export default function ExecutionChat({ messages, status, error }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && status === 'connected' && (
          <div className="text-center text-gray-400 py-8">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
            等待讨论开始...
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {error && (
          <div className="bg-red-900/50 text-red-400 p-3 rounded-lg">
            错误: {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {status === 'connecting' && (
        <div className="p-4 border-t border-gray-700 text-center text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
          连接中...
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: ExecutionMessage }) {
  const isUser = message.sender_type === 'user'
  const isSystem = message.sender_type === 'system'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-primary-600' : isSystem ? 'bg-gray-600' : 'bg-green-600'
      }`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
      </div>

      <div className={`max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        {message.sender_name && (
          <div className="text-xs text-gray-400 mb-1">
            {message.sender_name}
            {message.confidence && (
              <span className="ml-2 text-gray-500">
                置信度: {Math.round(message.confidence * 100)}%
              </span>
            )}
          </div>
        )}
        <div className={`p-3 rounded-lg ${
          isUser
            ? 'bg-primary-600 text-white'
            : isSystem
            ? 'bg-gray-700 text-gray-300'
            : 'bg-gray-700 text-white'
        }`}>
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Round {message.round} · {message.phase}
        </div>
      </div>
    </div>
  )
}
