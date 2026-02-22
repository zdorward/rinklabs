// apps/web/src/components/EdgeCard.tsx
import Link from 'next/link'
import { EdgeOpportunity } from '@/lib/api'
import { formatOdds, formatDateTime, getEdgeColor } from '@/lib/utils'

interface EdgeCardProps {
  edge: EdgeOpportunity
}

export function EdgeCard({ edge }: EdgeCardProps) {
  return (
    <Link href={`/games/${edge.game_id}`}>
      <div className="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <div className="flex justify-between items-start mb-2">
          <div>
            <p className="text-sm text-gray-500">{formatDateTime(edge.commence_time)}</p>
            <p className="font-medium">
              {edge.away_team} @ {edge.home_team}
            </p>
          </div>
          <span className={`text-lg font-bold ${getEdgeColor(edge.ev_pct)}`}>
            +{edge.ev_pct.toFixed(1)}% EV
          </span>
        </div>
        <div className="flex justify-between text-sm text-gray-600">
          <span>
            {edge.side === 'home' ? edge.home_team : edge.away_team} ML
          </span>
          <span>
            {edge.bookmaker}: {formatOdds(edge.book_price)}
          </span>
        </div>
      </div>
    </Link>
  )
}
