/**
 * Extract a human-readable message from an unknown thrown value.
 *
 * Prefers an axios-style `response.data.detail`, then a plain `message`, then a
 * caller-supplied fallback (or `String(err)` if none). Centralizes the error
 * handling that used to be sprinkled around as `(err as any).message`.
 */
export function getErrorMessage(err: unknown, fallback?: string): string {
  if (err && typeof err === 'object') {
    const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    if (typeof detail === 'string' && detail) return detail
    if (detail) return JSON.stringify(detail)

    const message = (err as { message?: unknown }).message
    if (typeof message === 'string' && message) return message
  }
  if (typeof err === 'string' && err) return err
  return fallback ?? String(err)
}
