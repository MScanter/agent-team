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
    <div className="w-96 border-r-4 border-black bg-[#2d2d2d] flex flex-col font-pixel">
      <div className="p-4 border-b-4 border-black bg-[#1a1a1a]">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-press text-white uppercase tracking-tighter">WORKSPACE</div>
          <div className="flex items-center gap-2">
            <button
              className="btn btn-outline p-2"
              onClick={() => void pickWorkspace()}
              disabled={isSettingWorkspace}
              title="选择工作目录"
            >
              <FolderOpen className="w-4 h-4" />
            </button>
            {workspacePath && (
              <button
                className="btn btn-outline p-2 text-red-500 border-red-500 hover:bg-red-900 shadow-pixel-sm"
                onClick={() => void clearWorkspace()}
                disabled={isSettingWorkspace}
                title="清除工作目录"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        <div className="text-[10px] text-primary-400 break-all uppercase leading-tight bg-black/40 p-2 border-2 border-black">
          {workspacePath || '[ NOT SET - CHOOSE A DIRECTORY ]'}
        </div>
      </div>

      <div className="p-3 border-b-2 border-black flex items-center justify-between gap-2 bg-[#252525]">
        <div className="text-[10px] font-press text-gray-500 truncate uppercase">
          DIR: {currentDir ? `/${currentDir}` : '/'}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            className="btn btn-outline p-1"
            onClick={goUp}
            disabled={!currentDir || !canList}
            title="上一级"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
          <button
            className="btn btn-outline p-1"
            onClick={() => void refreshList()}
            disabled={!canList || isListing}
            title="刷新"
          >
            <RefreshCw className={`w-4 h-4 ${isListing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {!workspacePath ? (
        <div className="p-6 text-xs text-gray-400 uppercase leading-relaxed text-center italic opacity-60">
          选择一个工作目录后，可以在这里浏览和编辑文件（将通过 RUST COMMAND 读取/写入）。
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {entries.length === 0 && !isListing ? (
            <div className="p-6 text-xs text-gray-500 text-center uppercase tracking-tighter">[ 目录为空 ]</div>
          ) : (
            <ul className="divide-y-2 divide-black">
              {entries.map((entry) => (
                <li key={entry.path}>
                  <button
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-primary-600 group transition-all"
                    onClick={() => void openEntry(entry)}
                    title={entry.path}
                  >
                    {entry.is_dir ? (
                      <Folder className="w-5 h-5 text-blue-400 group-hover:text-white flex-shrink-0" />
                    ) : (
                      <FileText className="w-5 h-5 text-gray-400 group-hover:text-white flex-shrink-0" />
                    )}
                    <span className="text-xs text-gray-200 group-hover:text-white truncate flex-1 uppercase tracking-tight">
                      {basename(entry.path)}{entry.is_dir ? '/' : ''}
                    </span>
                    {!entry.is_dir && typeof entry.size === 'number' && (
                      <span className="text-[10px] text-gray-500 group-hover:text-white flex-shrink-0 font-press">
                        {entry.size} B
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
        <div className="border-t-4 border-black flex flex-col h-72 bg-[#1a1a1a]">
          <div className="p-3 border-b-2 border-black bg-[#2d2d2d] flex items-center justify-between gap-2">
            <div className="text-[10px] font-press text-primary-400 truncate uppercase" title={selectedPath}>
              EDIT: {basename(selectedPath)}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {saveBanner && (
                <span className="text-[10px] font-press text-green-500 animate-pulse">{saveBanner}</span>
              )}
              <button
                className="btn btn-primary p-2"
                onClick={() => void saveFile()}
                disabled={!isDirty || isSaving || isReading}
                title="保存"
              >
                <Save className="w-4 h-4" />
              </button>
            </div>
          </div>
          <textarea
            className="flex-1 w-full px-4 py-3 bg-black text-gray-200 text-xs font-mono resize-none focus:outline-none"
            value={editorContent}
            onChange={(e) => setEditorContent(e.target.value)}
            disabled={isReading}
            spellCheck={false}
          />
        </div>
      )}

      {error && (
        <div className="p-4 border-t-4 border-black bg-red-900/50 text-red-300 text-[10px] font-press uppercase tracking-tighter leading-relaxed">
          ERROR: {error}
        </div>
      )}
    </div>
  )
}

