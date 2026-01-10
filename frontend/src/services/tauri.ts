export function isTauriApp() {
  return (
    typeof window !== 'undefined' &&
    (Boolean((window as any).__TAURI__) || Boolean((window as any).__TAURI_INTERNALS__))
  )
}

export async function tauriInvoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke<T>(command, args)
}

export async function tauriListen<TPayload>(
  eventName: string,
  handler: (payload: TPayload) => void,
): Promise<() => void> {
  const { listen } = await import('@tauri-apps/api/event')
  const unlisten = await listen<TPayload>(eventName, (event) => handler(event.payload))
  return unlisten
}

export async function tauriSelectDirectory(): Promise<string | null> {
  const { open } = await import('@tauri-apps/plugin-dialog')
  const selected = await open({ directory: true, multiple: false })
  if (!selected) return null
  if (Array.isArray(selected)) return selected[0] ? String(selected[0]) : null
  return String(selected)
}
