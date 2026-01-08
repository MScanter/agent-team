import { Link } from 'react-router-dom'
import { Bot, Users, Play, Sparkles } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">
          agent-team
        </h1>
        <p className="text-xl text-gray-400">
          创建和编排你的 AI Agent 团队
        </p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <Link
          to="/agents"
          className="card hover:border-primary-500 border border-transparent transition-colors group"
        >
          <Bot className="w-12 h-12 text-primary-500 mb-4 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-semibold text-white mb-2">创建 Agent</h2>
          <p className="text-gray-400">
            定义专业的 AI Agent，配置系统提示词、能力和行为
          </p>
        </Link>

        <Link
          to="/teams"
          className="card hover:border-primary-500 border border-transparent transition-colors group"
        >
          <Users className="w-12 h-12 text-green-500 mb-4 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-semibold text-white mb-2">组建团队</h2>
          <p className="text-gray-400">
            将多个 Agent 组合成团队，配置协作模式
          </p>
        </Link>

        <Link
          to="/teams"
          className="card hover:border-primary-500 border border-transparent transition-colors group"
        >
          <Play className="w-12 h-12 text-purple-500 mb-4 group-hover:scale-110 transition-transform" />
          <h2 className="text-xl font-semibold text-white mb-2">开始讨论</h2>
          <p className="text-gray-400">
            选择团队，输入问题，启动多 Agent 协作讨论
          </p>
        </Link>
      </div>

      {/* Features */}
      <div className="card">
        <div className="flex items-center mb-6">
          <Sparkles className="w-6 h-6 text-yellow-500 mr-2" />
          <h2 className="text-2xl font-semibold text-white">核心特性</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 bg-gray-700/50 rounded-lg">
            <h3 className="text-lg font-medium text-white mb-2">多种协作模式</h3>
            <p className="text-gray-400 text-sm">
              圆桌讨论、流水线处理、对抗辩论、自由协作 —— 选择最适合你场景的模式
            </p>
          </div>

          <div className="p-4 bg-gray-700/50 rounded-lg">
            <h3 className="text-lg font-medium text-white mb-2">灵活的 Agent 配置</h3>
            <p className="text-gray-400 text-sm">
              自定义系统提示词、选择模型、配置工具和知识库
            </p>
          </div>

          <div className="p-4 bg-gray-700/50 rounded-lg">
            <h3 className="text-lg font-medium text-white mb-2">实时流式输出</h3>
            <p className="text-gray-400 text-sm">
              通过 SSE 实时查看每个 Agent 的发言和讨论进展
            </p>
          </div>

          <div className="p-4 bg-gray-700/50 rounded-lg">
            <h3 className="text-lg font-medium text-white mb-2">成本控制</h3>
            <p className="text-gray-400 text-sm">
              Token 预算管理，实时成本追踪，智能模型路由
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
