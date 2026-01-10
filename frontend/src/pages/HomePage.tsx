import { Link } from 'react-router-dom'
import { Bot, Users, Play, Sparkles } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="p-8 font-pixel">
      {/* Header */}
      <div className="mb-12 border-b-4 border-black pb-8">
        <h1 className="text-5xl font-press text-white mb-6 tracking-tighter">
          AGENT-TEAM
        </h1>
        <p className="text-2xl text-primary-400 uppercase tracking-widest">
          [ 创建和编排你的 AI AGENT 团队 ]
        </p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        <Link
          to="/agents"
          className="card hover:bg-gray-700 transition-all group hover:-translate-y-1 active:translate-y-0"
        >
          <Bot className="w-16 h-16 text-primary-500 mb-6 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-press text-white mb-4">创建 AGENT</h2>
          <p className="text-gray-400 leading-relaxed">
            定义专业的 AI AGENT，配置系统提示词、能力和行为
          </p>
        </Link>

        <Link
          to="/teams"
          className="card hover:bg-gray-700 transition-all group hover:-translate-y-1 active:translate-y-0"
        >
          <Users className="w-16 h-16 text-green-500 mb-6 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-press text-white mb-4">组建团队</h2>
          <p className="text-gray-400 leading-relaxed">
            将多个 AGENT 组合成团队，配置协作模式
          </p>
        </Link>

        <Link
          to="/execution"
          className="card hover:bg-gray-700 transition-all group hover:-translate-y-1 active:translate-y-0"
        >
          <Play className="w-16 h-16 text-purple-500 mb-6 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-press text-white mb-4">开始讨论</h2>
          <p className="text-gray-400 leading-relaxed">
            选择团队，输入问题，启动多 AGENT 协作讨论
          </p>
        </Link>
      </div>

      {/* Features */}
      <div className="card">
        <div className="flex items-center mb-8 border-b-2 border-black pb-4">
          <Sparkles className="w-8 h-8 text-yellow-500 mr-4" />
          <h2 className="text-2xl font-press text-white">核心特性</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="p-6 bg-black/30 border-2 border-black">
            <h3 className="text-lg font-press text-primary-400 mb-4 uppercase">多种协作模式</h3>
            <p className="text-gray-400">
              圆桌讨论、流水线处理、对抗辩论、自由协作 —— 选择最适合你场景的模式
            </p>
          </div>

          <div className="p-6 bg-black/30 border-2 border-black">
            <h3 className="text-lg font-press text-primary-400 mb-4 uppercase">灵活的 AGENT 配置</h3>
            <p className="text-gray-400">
              自定义系统提示词、选择模型、配置工具和知识库
            </p>
          </div>

          <div className="p-6 bg-black/30 border-2 border-black">
            <h3 className="text-lg font-press text-primary-400 mb-4 uppercase">实时流式输出</h3>
            <p className="text-gray-400">
              通过 WebSocket 实时查看每个 AGENT 的发言和讨论进展
            </p>
          </div>

          <div className="p-6 bg-black/30 border-2 border-black">
            <h3 className="text-lg font-press text-primary-400 mb-4 uppercase">成本控制</h3>
            <p className="text-gray-400">
              TOKEN 预算管理，实时成本追踪，智能模型路由
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
