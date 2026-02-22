// apps/web/src/components/OddsTable.tsx
import { BookOdds } from '@/lib/api'
import { formatOdds, formatProbability, getEdgeColor } from '@/lib/utils'

interface OddsTableProps {
  odds: BookOdds[]
  homeTeam: string
  awayTeam: string
}

export function OddsTable({ odds, homeTeam, awayTeam }: OddsTableProps) {
  if (odds.length === 0) {
    return (
      <div className="text-center text-gray-500 py-8">
        No odds available yet
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-3 px-2">Bookmaker</th>
            <th className="text-center py-3 px-2">{homeTeam}</th>
            <th className="text-center py-3 px-2">{awayTeam}</th>
            <th className="text-center py-3 px-2">Home Fair</th>
            <th className="text-center py-3 px-2">Away Fair</th>
            <th className="text-center py-3 px-2">Home Edge</th>
            <th className="text-center py-3 px-2">Away Edge</th>
          </tr>
        </thead>
        <tbody>
          {odds.map((book) => (
            <tr key={book.bookmaker} className="border-b hover:bg-gray-50">
              <td className="py-3 px-2 font-medium capitalize">
                {book.bookmaker.replace(/_/g, ' ')}
              </td>
              <td className="text-center py-3 px-2 font-mono">
                {formatOdds(book.home_price)}
              </td>
              <td className="text-center py-3 px-2 font-mono">
                {formatOdds(book.away_price)}
              </td>
              <td className="text-center py-3 px-2">
                {formatProbability(book.home_vig_free_prob)}
              </td>
              <td className="text-center py-3 px-2">
                {formatProbability(book.away_vig_free_prob)}
              </td>
              <td className={`text-center py-3 px-2 font-medium ${getEdgeColor(book.home_edge_ev)}`}>
                {book.home_edge_ev > 0 ? '+' : ''}{book.home_edge_ev.toFixed(1)}%
              </td>
              <td className={`text-center py-3 px-2 font-medium ${getEdgeColor(book.away_edge_ev)}`}>
                {book.away_edge_ev > 0 ? '+' : ''}{book.away_edge_ev.toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
