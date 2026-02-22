// apps/web/src/lib/utils.ts
export function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`
}

export function formatProbability(prob: number): string {
  return `${(prob * 100).toFixed(1)}%`
}

export function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function getEdgeColor(evPct: number): string {
  if (evPct >= 5) return 'text-green-600'
  if (evPct >= 2) return 'text-green-500'
  if (evPct > 0) return 'text-green-400'
  return 'text-gray-500'
}
