import { useState } from 'react'
import { Plus, Search, Users, MoreVertical, Trash2, Edit, Play } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTeams, useDeleteTeam } from '@/hooks'
import { TeamForm } from '@/components/Team'
import type { Team, TeamListItem } from '@/types'
import { teamApi } from '@/services/api'

const modeLabels: Record<string, string> = {
  roundtable: '圆桌讨论',
  pipeline: '流水线',
  debate: '对抗辩论',
  freeform: '自由协作',
  custom: '自定义',
}

const modeColors: Record<string, string> = {
  roundtable: 'bg-blue-900/50 text-blue-400',
  pipeline: 'bg-purple-900/50 text-purple-400',
  debate: 'bg-red-900/50 text-red-400',
  freeform: 'bg-green-900/50 text-green-400',
  custom: 'bg-gray-700 text-gray-400',
}

export default function TeamsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editTeam, setEditTeam] = useState<Team | null>(null)
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  const { data, isLoading } = useTeams({ search: search || undefined })
  const deleteTeam = useDeleteTeam()

  const handleEdit = async (team: TeamListItem) => {
    const fullTeam = await teamApi.get(team.id)
    setEditTeam(fullTeam)
    setShowForm(true)
    setMenuOpen(null)
  }

  const handleDelete = async (id: string) => {
    if (confirm('确定删除此团队?')) {
      await deleteTeam.mutateAsync(id)
    }
    setMenuOpen(null)
  }

  const handleStart = (teamId: string) => {
    navigate(`/execution?team=${teamId}`)
    setMenuOpen(null)
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">团队</h1>
          <p className="text-gray-400">管理你的 Agent 团队配置</p>
        </div>
        <button className="btn btn-primary flex items-center" onClick={() => { setEditTeam(null); setShowForm(true) }}>
          <Plus className="w-5 h-5 mr-2" />
          创建团队
        </button>
      </div>

      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="搜索团队..."
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
          <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">还没有团队</h3>
          <p className="text-gray-400 mb-6">创建你的第一个 Agent 团队开始协作</p>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            <Plus className="w-5 h-5 mr-2 inline" />
            创建团队
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data?.items.map((team: TeamListItem) => (
            <TeamCard
              key={team.id}
              team={team}
              menuOpen={menuOpen === team.id}
              onMenuToggle={() => setMenuOpen(menuOpen === team.id ? null : team.id)}
              onEdit={() => handleEdit(team)}
              onDelete={() => handleDelete(team.id)}
              onStart={() => handleStart(team.id)}
            />
          ))}
        </div>
      )}

      {showForm && (
        <TeamForm team={editTeam} onClose={() => { setShowForm(false); setEditTeam(null) }} />
      )}
    </div>
  )
}

function TeamCard({
  team,
  menuOpen,
  onMenuToggle,
  onEdit,
  onDelete,
  onStart,
}: {
  team: TeamListItem
  menuOpen: boolean
  onMenuToggle: () => void
  onEdit: () => void
  onDelete: () => void
  onStart: () => void
}) {
  return (
    <div className="card hover:border-primary-500 border border-transparent transition-colors relative">
      <div className="absolute top-3 right-3">
        <button onClick={onMenuToggle} className="text-gray-400 hover:text-white p-1">
          <MoreVertical className="w-4 h-4" />
        </button>
        {menuOpen && (
          <div className="absolute right-0 mt-1 bg-gray-700 rounded-lg shadow-lg py-1 min-w-[120px] z-10">
            <button onClick={onStart} className="w-full px-3 py-2 text-left text-sm text-green-400 hover:bg-gray-600 flex items-center">
              <Play className="w-4 h-4 mr-2" /> 开始讨论
            </button>
            <button onClick={onEdit} className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-600 flex items-center">
              <Edit className="w-4 h-4 mr-2" /> 编辑
            </button>
            <button onClick={onDelete} className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-gray-600 flex items-center">
              <Trash2 className="w-4 h-4 mr-2" /> 删除
            </button>
          </div>
        )}
      </div>

      <div className="flex items-start mb-4 pr-8">
        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary-600 to-purple-600 flex items-center justify-center">
          {team.icon ? (
            <img src={team.icon} alt={team.name} className="w-8 h-8" />
          ) : (
            <Users className="w-6 h-6 text-white" />
          )}
        </div>
        <div className="ml-4 flex-1">
          <h3 className="text-lg font-semibold text-white">{team.name}</h3>
          <p className="text-sm text-gray-400">{team.member_count ?? 0} 个成员</p>
        </div>
      </div>

      {team.description && (
        <p className="text-gray-400 text-sm mb-4 line-clamp-2">{team.description}</p>
      )}

      <div className="flex items-center justify-between text-sm">
        <span className={`px-2 py-1 rounded-full ${modeColors[team.collaboration_mode] || modeColors.custom}`}>
          {modeLabels[team.collaboration_mode] || team.collaboration_mode}
        </span>
        <span className="text-gray-500">使用 {team.usage_count} 次</span>
      </div>
    </div>
  )
}
