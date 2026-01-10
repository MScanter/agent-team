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
    <div className="flex flex-col h-full font-pixel">
      <div className="flex-1 overflow-y-auto p-6 space-y-8 bg-[#1a1a1a]">
        {messages.length === 0 && (status === 'connected' || status === 'connecting') && (
          <div className="text-center text-gray-500 py-12 uppercase tracking-widest">
            <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4 text-primary-500" />
            [ WAITING FOR DISCUSSION TO START... ]
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {error && (
          <div className="bg-red-900/50 text-red-400 p-4 border-2 border-red-500 shadow-pixel-sm uppercase text-xs">
            ERROR: {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {status === 'connecting' && (
        <div className="p-4 border-t-4 border-black bg-[#2d2d2d] text-center text-gray-400 uppercase text-[10px] font-press tracking-tighter">
          <Loader2 className="w-4 h-4 animate-spin inline mr-3" />
          CONNECTING...
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: ExecutionMessage }) {
  const isUser = message.sender_type === 'user'
  const isSystem = message.sender_type === 'system'

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''} group`}>
      <div className={`w-12 h-12 border-4 border-black flex items-center justify-center flex-shrink-0 shadow-pixel-sm ${
        isUser ? 'bg-primary-600' : isSystem ? 'bg-gray-600' : 'bg-green-600'
      }`}>
        {isUser ? <User className="w-6 h-6 text-white" /> : <Bot className="w-6 h-6 text-white" />}
      </div>

      <div className={`max-w-[85%] ${isUser ? 'text-right' : ''}`}>
        {message.sender_name && (
          <div className="text-[10px] font-press text-primary-400 mb-2 uppercase tracking-tighter">
            {message.sender_name}
            {message.confidence && (
              <span className="ml-3 text-gray-500">
                CONF: {Math.round(message.confidence * 100)}%
              </span>
            )}
          </div>
        )}
        <div className={`p-4 border-4 border-black shadow-pixel transition-transform group-hover:translate-x-[2px] group-hover:translate-y-[2px] group-hover:shadow-pixel-sm ${
          isUser
            ? 'bg-primary-600 text-white'
            : isSystem
            ? 'bg-[#333] text-gray-400'
            : 'bg-[#2d2d2d] text-white'
        }`}>
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
        <div className="text-[10px] font-press text-gray-500 mt-3 uppercase tracking-tighter">
          ROUND {message.round} · {message.phase}
        </div>
      </div>
    </div>
  )
}
