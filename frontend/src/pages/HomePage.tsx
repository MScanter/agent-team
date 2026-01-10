import { Link } from 'react-router-dom'
import { Bot, Users, Play, Sparkles } from 'lucide-react'
import { PixelLogo } from '@/components/Common/PixelLogo'

export default function HomePage() {
  return (
    <div className="p-6 font-pixel max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 border-b-4 border-black pb-4 flex items-baseline justify-between">
        <div className="flex items-center gap-4">
          <PixelLogo className="w-10 h-10 text-primary-500" />
          <div>
            <h1 className="text-3xl font-press text-white mb-2 tracking-tighter">
              AGENT-TEAM
            </h1>
            <p className="text-sm text-primary-400 uppercase tracking-widest">
              [ 创建和编排你的 AI AGENT 团队 ]
            </p>
          </div>
        </div>
        <div className="text-[10px] font-press text-gray-500 uppercase animate-pulse">
          v1.0.0 Ready_
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Link
          to="/agents"
          className="card p-4 hover:bg-[#3d3d3d] transition-all group hover:-translate-y-1 active:translate-y-0"
        >
          <div className="flex items-center gap-4 mb-3">
            <Bot className="w-10 h-10 text-primary-500 group-hover:scale-110 transition-transform" />
            <h2 className="text-sm font-press text-white">创建 AGENT</h2>
          </div>
          <p className="text-xs text-gray-400 leading-tight">
            定义专业的 AI AGENT，配置系统提示词、能力和行为。
          </p>
        </Link>

        <Link
          to="/teams"
          className="card p-4 hover:bg-[#3d3d3d] transition-all group hover:-translate-y-1 active:translate-y-0"
        >
          <div className="flex items-center gap-4 mb-3">
            <Users className="w-10 h-10 text-green-500 group-hover:scale-110 transition-transform" />
            <h2 className="text-sm font-press text-white">组建团队</h2>
          </div>
          <p className="text-xs text-gray-400 leading-tight">
            将多个 AGENT 组合成团队，配置协作模式和流程。
          </p>
        </Link>

        <Link
          to="/execution"
          className="card p-4 hover:bg-[#3d3d3d] transition-all group hover:-translate-y-1 active:translate-y-0"
        >
          <div className="flex items-center gap-4 mb-3">
            <Play className="w-10 h-10 text-purple-500 group-hover:scale-110 transition-transform" />
            <h2 className="text-sm font-press text-white">开始讨论</h2>
          </div>
          <p className="text-xs text-gray-400 leading-tight">
            选择团队，输入问题，启动多 AGENT 实时协作讨论。
          </p>
        </Link>
      </div>

      {/* Features */}
      <div className="card p-5">
        <div className="flex items-center mb-4 border-b-2 border-black pb-3">
          <Sparkles className="w-6 h-6 text-yellow-500 mr-3" />
          <h2 className="text-sm font-press text-white">CORE_FEATURES</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-3 bg-black/30 border-2 border-black">
            <h3 className="text-[10px] font-press text-primary-400 mb-2 uppercase">多种模式</h3>
            <p className="text-[11px] text-gray-400 leading-normal">
              圆桌、流水线、对抗辩论、自由协作模式。
            </p>
          </div>

          <div className="p-3 bg-black/30 border-2 border-black">
            <h3 className="text-[10px] font-press text-primary-400 mb-2 uppercase">灵活配置</h3>
            <p className="text-[11px] text-gray-400 leading-normal">
              自定义提示词、模型、工具和知识库。
            </p>
          </div>

          <div className="p-3 bg-black/30 border-2 border-black">
            <h3 className="text-[10px] font-press text-primary-400 mb-2 uppercase">流式输出</h3>
            <p className="text-[11px] text-gray-400 leading-normal">
              实时查看每个 AGENT 的发言和进展。
            </p>
          </div>

          <div className="p-3 bg-black/30 border-2 border-black">
            <h3 className="text-[10px] font-press text-primary-400 mb-2 uppercase">成本控制</h3>
            <p className="text-[11px] text-gray-400 leading-normal">
              TOKEN 预算管理，实时成本追踪。
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
