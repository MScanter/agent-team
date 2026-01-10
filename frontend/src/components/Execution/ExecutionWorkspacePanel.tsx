import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowUp, FileText, Folder, FolderOpen, RefreshCw, Save, X } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import type { FileEntry } from '@/types'
import { executionApi } from '@/services/api'
import { tauriSelectDirectory } from '@/services/tauri'

function getErrorMessage(err: unknown) {
  if (err && typeof err === 'object' && 'message' in err && typeof (err as any).message === 'string') {
    return (err as any).message as string
  }
  return String(err)
}

function basename(path: string) {
  const parts = path.split('/').filter(Boolean)
  return parts.length ? parts[parts.length - 1] : path
}

function parentDir(path: string) {
  const parts = path.split('/').filter(Boolean)
  if (parts.length <= 1) return ''
  return parts.slice(0, -1).join('/')
}

export default function ExecutionWorkspacePanel({
  executionId,
  initialWorkspacePath,
}: {
  executionId: string
  initialWorkspacePath?: string | null
}) {
  const queryClient = useQueryClient()
  const [workspacePath, setWorkspacePath] = useState<string | null>(initialWorkspacePath || null)
  const [currentDir, setCurrentDir] = useState<string>('')
  const [entries, setEntries] = useState<FileEntry[]>([])
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [editorContent, setEditorContent] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [isListing, setIsListing] = useState(false)
  const [isReading, setIsReading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isSettingWorkspace, setIsSettingWorkspace] = useState(false)
  const [saveBanner, setSaveBanner] = useState<string | null>(null)

  useEffect(() => {
    setWorkspacePath(initialWorkspacePath || null)
    setCurrentDir('')
    setEntries([])
    setSelectedPath(null)
    setFileContent('')
    setEditorContent('')
    setError(null)
    setSaveBanner(null)
  }, [executionId])

  const canList = Boolean(workspacePath)

  const refreshList = useCallback(async () => {
    if (!workspacePath) {
      setEntries([])
      return
    }

    setIsListing(true)
    setError(null)
    try {
      const items = await executionApi.listFiles(executionId, currentDir || undefined)
      setEntries(items)
    } catch (e) {
      setEntries([])
      setError(getErrorMessage(e))
    } finally {
      setIsListing(false)
    }
  }, [currentDir, executionId, workspacePath])

  useEffect(() => {
    void refreshList()
  }, [refreshList])

  const pickWorkspace = useCallback(async () => {
    setError(null)
    setSaveBanner(null)
    const dir = await tauriSelectDirectory()
    if (!dir) return

    setIsSettingWorkspace(true)
    try {
      await executionApi.setWorkspace(executionId, dir)
      setWorkspacePath(dir)
      setCurrentDir('')
      setSelectedPath(null)
      setFileContent('')
      setEditorContent('')
      queryClient.invalidateQueries({ queryKey: ['execution', executionId] })
      await refreshList()
    } catch (e) {
      setError(getErrorMessage(e))
    } finally {
      setIsSettingWorkspace(false)
    }
  }, [executionId, queryClient, refreshList])

  const clearWorkspace = useCallback(async () => {
    setError(null)
    setSaveBanner(null)
    setIsSettingWorkspace(true)
    try {
      await executionApi.setWorkspace(executionId, null)
      setWorkspacePath(null)
      setCurrentDir('')
      setEntries([])
      setSelectedPath(null)
      setFileContent('')
      setEditorContent('')
      queryClient.invalidateQueries({ queryKey: ['execution', executionId] })
    } catch (e) {
      setError(getErrorMessage(e))
    } finally {
      setIsSettingWorkspace(false)
    }
  }, [executionId, queryClient])

  const openEntry = useCallback(async (entry: FileEntry) => {
    setError(null)
    setSaveBanner(null)

    if (entry.is_dir) {
      setCurrentDir(entry.path)
      setSelectedPath(null)
      setFileContent('')
      setEditorContent('')
      return
    }

    setSelectedPath(entry.path)
    setIsReading(true)
    try {
      const text = await executionApi.readFile(executionId, entry.path)
      setFileContent(text)
      setEditorContent(text)
    } catch (e) {
      setError(getErrorMessage(e))
    } finally {
      setIsReading(false)
    }
  }, [executionId])

  const goUp = useCallback(() => {
    setCurrentDir((prev) => parentDir(prev))
    setSelectedPath(null)
    setFileContent('')
    setEditorContent('')
    setSaveBanner(null)
  }, [])

  const isDirty = useMemo(() => {
    if (!selectedPath) return false
    return editorContent !== fileContent
  }, [editorContent, fileContent, selectedPath])

  const saveFile = useCallback(async () => {
    if (!selectedPath) return
    setError(null)
    setIsSaving(true)
    try {
      await executionApi.writeFile(executionId, selectedPath, editorContent)
      setFileContent(editorContent)
      setSaveBanner('已保存')
      void refreshList()
      window.setTimeout(() => setSaveBanner(null), 1200)
    } catch (e) {
      setError(getErrorMessage(e))
    } finally {
      setIsSaving(false)
    }
  }, [editorContent, executionId, refreshList, selectedPath])

  return (
    <div className="w-96 border-r border-gray-700 bg-gray-900/50 flex flex-col">
      <div className="p-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-white">工作目录</div>
          <div className="flex items-center gap-2">
            <button
              className="btn btn-outline px-3 py-1 text-sm"
              onClick={() => void pickWorkspace()}
              disabled={isSettingWorkspace}
              title="选择工作目录"
            >
              <FolderOpen className="w-4 h-4 inline mr-1" />
              选择
            </button>
            {workspacePath && (
              <button
                className="btn btn-outline px-3 py-1 text-sm"
                onClick={() => void clearWorkspace()}
                disabled={isSettingWorkspace}
                title="清除工作目录"
              >
                <X className="w-4 h-4 inline mr-1" />
                清除
              </button>
            )}
          </div>
        </div>
        <div className="mt-1 text-xs text-gray-400 break-all">
          {workspacePath || '未设置（选择目录后启用文件操作）'}
        </div>
      </div>

      <div className="p-3 border-b border-gray-700 flex items-center justify-between gap-2">
        <div className="text-xs text-gray-400 truncate">
          {currentDir ? `/${currentDir}` : '/'}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            className="btn btn-outline px-2 py-1"
            onClick={goUp}
            disabled={!currentDir || !canList}
            title="上一级"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
          <button
            className="btn btn-outline px-2 py-1"
            onClick={() => void refreshList()}
            disabled={!canList || isListing}
            title="刷新"
          >
            <RefreshCw className={`w-4 h-4 ${isListing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {!workspacePath ? (
        <div className="p-4 text-sm text-gray-400">
          选择一个工作目录后，可以在这里浏览和编辑文件（将通过 Rust command 读取/写入）。
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {entries.length === 0 && !isListing ? (
            <div className="p-4 text-sm text-gray-400">该目录为空。</div>
          ) : (
            <ul className="divide-y divide-gray-800">
              {entries.map((entry) => (
                <li key={entry.path}>
                  <button
                    className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-800/50 transition-colors"
                    onClick={() => void openEntry(entry)}
                    title={entry.path}
                  >
                    {entry.is_dir ? (
                      <Folder className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    ) : (
                      <FileText className="w-4 h-4 text-gray-300 flex-shrink-0" />
                    )}
                    <span className="text-sm text-gray-200 truncate flex-1">
                      {basename(entry.path)}{entry.is_dir ? '/' : ''}
                    </span>
                    {!entry.is_dir && typeof entry.size === 'number' && (
                      <span className="text-xs text-gray-500 flex-shrink-0">
                        {entry.size.toLocaleString()} B
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {selectedPath && workspacePath && (
        <div className="border-t border-gray-700 flex flex-col h-64">
          <div className="p-2 border-b border-gray-700 flex items-center justify-between gap-2">
            <div className="text-xs text-gray-400 truncate" title={selectedPath}>
              {selectedPath}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {saveBanner && (
                <span className="text-xs text-green-400">{saveBanner}</span>
              )}
              <button
                className="btn btn-primary px-3 py-1 text-sm"
                onClick={() => void saveFile()}
                disabled={!isDirty || isSaving || isReading}
                title="保存"
              >
                <Save className="w-4 h-4 inline mr-1" />
                保存
              </button>
            </div>
          </div>
          <textarea
            className="flex-1 w-full px-3 py-2 bg-gray-900 text-gray-200 text-sm resize-none focus:outline-none"
            value={editorContent}
            onChange={(e) => setEditorContent(e.target.value)}
            disabled={isReading}
            spellCheck={false}
          />
        </div>
      )}

      {error && (
        <div className="p-3 border-t border-gray-700 bg-red-900/20 text-red-300 text-xs break-words">
          {error}
        </div>
      )}
    </div>
  )
}

