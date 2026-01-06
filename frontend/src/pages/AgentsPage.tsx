import { useState } from 'react'
import { Plus, Search, Bot, MoreVertical, Copy, Trash2, Edit } from 'lucide-react'
import { useAgents, useDeleteAgent, useDuplicateAgent } from '@/hooks'
import { AgentForm } from '@/components/Agent'
import type { Agent, AgentListItem } from '@/types'
import { agentApi } from '@/services/api'

export default function AgentsPage() {
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editAgent, setEditAgent] = useState<Agent | null>(null)
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  const { data, isLoading } = useAgents({ search: search || undefined })
  const deleteAgent = useDeleteAgent()
  const duplicateAgent = useDuplicateAgent()

  const handleEdit = async (agent: AgentListItem) => {
    const fullAgent = await agentApi.get(agent.id)
    setEditAgent(fullAgent)
    setShowForm(true)
    setMenuOpen(null)
  }

  const handleDelete = async (id: string) => {
    if (confirm('确定删除此 Agent?')) {
      await deleteAgent.mutateAsync(id)
    }
    setMenuOpen(null)
  }

  const handleDuplicate = async (id: string) => {
    await duplicateAgent.mutateAsync({ id })
    setMenuOpen(null)
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Agents</h1>
          <p className="text-gray-400">管理你的 AI Agent 配置</p>
        </div>
        <button className="btn btn-primary flex items-center" onClick={() => { setEditAgent(null); setShowForm(true) }}>
          <Plus className="w-5 h-5 mr-2" />
          创建 Agent
        </button>
      </div>

      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="搜索 Agent..."
            className="input pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : data?.items.length === 0 ? (
        <div className="card text-center py-12">
          <Bot className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">还没有 Agent</h3>
          <p className="text-gray-400 mb-6">创建你的第一个 AI Agent 开始使用</p>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            <Plus className="w-5 h-5 mr-2 inline" />
            创建 Agent
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.items.map((agent: AgentListItem) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              menuOpen={menuOpen === agent.id}
              onMenuToggle={() => setMenuOpen(menuOpen === agent.id ? null : agent.id)}
              onEdit={() => handleEdit(agent)}
              onDelete={() => handleDelete(agent.id)}
              onDuplicate={() => handleDuplicate(agent.id)}
            />
          ))}
        </div>
      )}

      {showForm && (
        <AgentForm agent={editAgent} onClose={() => { setShowForm(false); setEditAgent(null) }} />
      )}
    </div>
  )
}

function AgentCard({
  agent,
  menuOpen,
  onMenuToggle,
  onEdit,
  onDelete,
  onDuplicate,
}: {
  agent: AgentListItem
  menuOpen: boolean
  onMenuToggle: () => void
  onEdit: () => void
  onDelete: () => void
  onDuplicate: () => void
}) {
  return (
    <div className="card hover:border-primary-500 border border-transparent transition-colors relative">
      <div className="absolute top-3 right-3">
        <button onClick={onMenuToggle} className="text-gray-400 hover:text-white p-1">
          <MoreVertical className="w-4 h-4" />
        </button>
        {menuOpen && (
          <div className="absolute right-0 mt-1 bg-gray-700 rounded-lg shadow-lg py-1 min-w-[120px] z-10">
            <button onClick={onEdit} className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-600 flex items-center">
              <Edit className="w-4 h-4 mr-2" /> 编辑
            </button>
            <button onClick={onDuplicate} className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-600 flex items-center">
              <Copy className="w-4 h-4 mr-2" /> 复制
            </button>
            <button onClick={onDelete} className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-gray-600 flex items-center">
              <Trash2 className="w-4 h-4 mr-2" /> 删除
            </button>
          </div>
        )}
      </div>

      <div className="flex items-start mb-4 pr-8">
        <div className="w-12 h-12 rounded-full bg-primary-600 flex items-center justify-center text-white font-bold text-lg">
          {agent.avatar ? (
            <img src={agent.avatar} alt={agent.name} className="w-full h-full rounded-full object-cover" />
          ) : (
            agent.name.charAt(0).toUpperCase()
          )}
        </div>
        <div className="ml-4 flex-1">
          <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
          <p className="text-sm text-gray-400">{agent.domain || '通用'}</p>
        </div>
      </div>

      {agent.description && (
        <p className="text-gray-400 text-sm mb-4 line-clamp-2">{agent.description}</p>
      )}

      <div className="flex items-center justify-between text-sm">
        <span className={`px-2 py-1 rounded-full ${
          agent.collaboration_style === 'dominant'
            ? 'bg-red-900/50 text-red-400'
            : agent.collaboration_style === 'critical'
            ? 'bg-yellow-900/50 text-yellow-400'
            : 'bg-green-900/50 text-green-400'
        }`}>
          {agent.collaboration_style === 'dominant' ? '主导型' :
           agent.collaboration_style === 'critical' ? '批判型' : '支持型'}
        </span>
        <span className="text-gray-500">使用 {agent.usage_count} 次</span>
      </div>
    </div>
  )
}
