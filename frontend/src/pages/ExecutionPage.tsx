import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Send, Pause, Play, Square } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useExecution, useCreateExecution, useControlExecution, useDeleteExecution, useExecutionSocket } from '@/hooks'
import { ExecutionChat } from '@/components/Execution'
import { buildExecutionLLMConfig } from '@/services/modelConfigStore'
import { isTauriApp } from '@/services/tauri'
import ExecutionWorkspacePanel from '@/components/Execution/ExecutionWorkspacePanel'

export default function ExecutionPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const teamId = searchParams.get('team')

  const [chatInput, setChatInput] = useState('')
  const [clientMessages, setClientMessages] = useState<any[]>([])
  const [isSendingFollowup, setIsSendingFollowup] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [executionId, setExecutionId] = useState<string | null>(id || null)
  const autoStartedRef = useRef(false)

  const { data: execution, isLoading } = useExecution(executionId || '')
  const createExecution = useCreateExecution()
  const controlExecution = useControlExecution()
  const deleteExecution = useDeleteExecution()
  const llm = buildExecutionLLMConfig()
  const { messages, status: streamStatus, error: streamError, sendFollowup, reconnect } =
    useExecutionSocket(executionId)

  const baseMessages = useMemo(() => {
    const merged = new Map<string, any>()
    const recent = execution?.recent_messages || []
    for (const m of recent) merged.set(m.id, m)
    for (const m of messages || []) merged.set(m.id, m)
    return Array.from(merged.values()).sort((a: any, b: any) => {
      const sa = Number(a.sequence || 0)
      const sb = Number(b.sequence || 0)
      if (sa !== sb) return sa - sb
      return String(a.created_at || '').localeCompare(String(b.created_at || ''))
    })
  }, [execution?.recent_messages, messages])

  const displayMessages = useMemo(() => {
    const merged = new Map<string, any>()
    for (const m of baseMessages) merged.set(m.id, m)
    for (const m of clientMessages) merged.set(m.id, m)
    return Array.from(merged.values()).sort((a: any, b: any) => {
      const sa = Number(a.sequence || 0)
      const sb = Number(b.sequence || 0)
      if (sa !== sb) return sa - sb
      return String(a.created_at || '').localeCompare(String(b.created_at || ''))
    })
  }, [baseMessages, clientMessages])

  useEffect(() => {
    setExecutionId(id || null)
  }, [id])

  useEffect(() => {
    if (executionId) {
      localStorage.setItem('agent-team:lastExecutionId', executionId)
      return
    }
    if (!id && !teamId) {
      const last = localStorage.getItem('agent-team:lastExecutionId')
      if (last) navigate(`/execution/${last}`)
    }
  }, [executionId, id, teamId, navigate])

  useEffect(() => {
    // If we enter from a team (e.g. /execution?team=...), create an execution immediately
    // so users always land in the discussion UI.
    if (!teamId) return
    if (id) return
    if (executionId) return
    if (autoStartedRef.current) return
    if (!llm) return

    autoStartedRef.current = true
    setStartError(null)
    void (async () => {
      try {
        const result = await createExecution.mutateAsync({
          team_id: teamId,
          input: '',
          title: undefined,
          llm,
        })
        setExecutionId(result.id)
        navigate(`/execution/${result.id}?team=${teamId}`)
      } catch (e: any) {
        autoStartedRef.current = false
        const detail = e?.response?.data?.detail
        setStartError(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : e?.message || '创建执行失败')
      }
    })()
  }, [createExecution, executionId, id, llm, navigate, teamId])

  const handleControl = async (action: string) => {
    if (!executionId) return
    await controlExecution.mutateAsync({ id: executionId, action })
  }

  const handleNewDiscussion = async () => {
    const resolvedTeamId = teamId || execution?.team_id
    if (!resolvedTeamId) {
      navigate('/teams')
      return
    }
    if (!llm) {
      setStartError('需要先在“API配置”里创建默认配置并填写 API Key。')
      return
    }

    setStartError(null)
    try {
      const result = await createExecution.mutateAsync({
        team_id: resolvedTeamId,
        input: '',
        title: undefined,
        llm,
      })
      setClientMessages([])
      setExecutionId(result.id)
      navigate(`/execution/${result.id}?team=${resolvedTeamId}`)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setStartError(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : e?.message || '创建执行失败')
    }
  }

  const handleDeleteDiscussion = async () => {
    if (!executionId) return
    if (!confirm('确定删除当前讨论？删除后无法恢复。')) return

    try {
      await deleteExecution.mutateAsync(executionId)
      const last = localStorage.getItem('agent-team:lastExecutionId')
      if (last === executionId) localStorage.removeItem('agent-team:lastExecutionId')
      setClientMessages([])
      setExecutionId(null)
      navigate('/teams')
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setStartError(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : e?.message || '删除失败')
    }
  }

  const handleFollowup = async () => {
    if (!executionId || !chatInput.trim()) return
    if (!execution) return

    const text = chatInput.trim()
    setChatInput('')

    if (execution.status === 'running') {
      await handleControl('pause')
    }

    setIsSendingFollowup(true)
    const ok = sendFollowup(text)
    if (!ok) {
      setClientMessages((prev) => [
        ...prev,
        {
          id: `${executionId}-sys-${Date.now()}-${Math.random().toString(16).slice(2)}`,
          sequence: 0,
          round: 0,
          phase: 'error',
          sender_type: 'system',
          sender_name: 'system',
          content: '追问失败: WebSocket 未连接',
          content_type: 'text',
          wants_to_continue: true,
          input_tokens: 0,
          output_tokens: 0,
          metadata: {},
          created_at: new Date().toISOString(),
        },
      ])
    }
    setIsSendingFollowup(false)
  }

  if (!executionId) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="card w-full max-w-lg">
          <h2 className="text-xl font-bold text-white mb-2">讨论</h2>
          <p className="text-sm text-gray-400 mb-4">从团队页面选择一个团队开始讨论。</p>
          <button className="btn btn-primary w-full" onClick={() => navigate('/teams')}>
            去选择团队
          </button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-400">加载中...</div>
      </div>
    )
  }

  if (!execution) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="card w-full max-w-lg">
          <h2 className="text-xl font-bold text-white mb-2">讨论不存在</h2>
          <p className="text-sm text-gray-400 mb-4">可能已被删除，或本地记录的 ID 已失效。</p>
          <button
            className="btn btn-secondary w-full mb-2"
            onClick={() => {
              localStorage.removeItem('agent-team:lastExecutionId')
              navigate('/teams')
            }}
          >
            去选择团队
          </button>
          <button className="btn btn-primary w-full" onClick={() => navigate('/execution')}>
            返回讨论入口
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div>
          <h1 className="text-xl font-bold text-white">讨论</h1>
          <p className="text-sm text-gray-400">
            状态: {execution.status} | 轮次: {execution.current_round}
            {streamStatus === 'connecting' && ' | 连接中...'}
            {streamStatus === 'error' && ' | 连接异常'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {streamStatus === 'error' && (
            <button className="btn btn-outline" onClick={() => reconnect()}>
              重连
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => void handleNewDiscussion()} disabled={!llm}>
            新讨论
          </button>

          {execution.status === 'running' ? (
            <button className="btn btn-secondary flex items-center" onClick={() => handleControl('pause')}>
              <Pause className="w-4 h-4 mr-2" />
              暂停
            </button>
          ) : execution.status === 'paused' ? (
            <button className="btn btn-primary flex items-center" onClick={() => handleControl('resume')}>
              <Play className="w-4 h-4 mr-2" />
              继续
            </button>
          ) : null}

          {['running', 'paused'].includes(execution.status) && (
            <button
              className="btn btn-outline flex items-center text-red-400 border-red-400 hover:bg-red-900/50"
              onClick={() => handleControl('stop')}
            >
              <Square className="w-4 h-4 mr-2" />
              结束
            </button>
          )}

          <button
            className="btn btn-outline flex items-center text-red-400 border-red-400 hover:bg-red-900/50"
            onClick={() => void handleDeleteDiscussion()}
            disabled={deleteExecution.isPending}
            title="删除当前讨论"
          >
            删除
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex">
        {isTauriApp() && (
          <ExecutionWorkspacePanel
            executionId={executionId}
            initialWorkspacePath={execution.workspace_path}
          />
        )}
        <div className="flex-1 overflow-hidden">
          <ExecutionChat messages={displayMessages} status={streamStatus} error={streamError} />
        </div>
      </div>

      <div className="px-4 py-2 border-t border-gray-700 bg-gray-800/50">
        <div className="flex items-center justify-between text-sm text-gray-400 mb-1">
          <span>Token 使用</span>
          <span>
            {execution.tokens_used.toLocaleString()} / {execution.tokens_budget.toLocaleString()}
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div
            className="bg-primary-500 h-2 rounded-full transition-all"
            style={{ width: `${Math.min(100, (execution.tokens_used / execution.tokens_budget) * 100)}%` }}
          />
        </div>
      </div>

      {execution.status === 'completed' && (
        <div className="p-4 border-t border-gray-700" />
      )}

      {execution.status !== 'failed' && (
        <div className="p-4 border-t border-gray-700">
          {!llm && (
            <div className="mb-3 text-sm text-yellow-300 bg-yellow-900/30 border border-yellow-800 rounded p-3">
              需要先在“API配置”里创建默认配置并填写 API Key。
              <button
                type="button"
                className="ml-2 underline text-yellow-200 hover:text-yellow-100"
                onClick={() => navigate('/models')}
              >
                去配置
              </button>
            </div>
          )}
          {startError && (
            <div className="mb-3 text-sm text-red-300 bg-red-900/30 border border-red-800 rounded p-3">
              创建失败：{startError}
            </div>
          )}
          <div className="flex items-center gap-2">
            <input
              type="text"
              className="input flex-1"
              placeholder="在讨论中输入关键词/追问（运行中会自动尝试暂停）..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && chatInput.trim()) {
                  e.preventDefault()
                  void handleFollowup()
                }
              }}
              disabled={!executionId || isSendingFollowup}
            />
            <button
              className="btn btn-primary"
              disabled={!chatInput.trim() || !executionId || isSendingFollowup}
              onClick={() => void handleFollowup()}
              title="发送追问"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            提示：后端只允许在暂停/完成状态处理追问；运行中会先请求暂停（可能需要等待当前一步完成）。
          </p>
        </div>
      )}
    </div>
  )
}
