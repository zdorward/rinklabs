// apps/web/src/components/DisagreementCard.tsx
import Link from 'next/link'
import { DisagreementInfo } from '@/lib/api'
import { formatDateTime, formatProbability } from '@/lib/utils'

interface DisagreementCardProps {
  disagreement: DisagreementInfo
}

export function DisagreementCard({ disagreement }: DisagreementCardProps) {
  return (
    <Link href={`/games/${disagreement.game_id}`}>
      <div className="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow">
        <div className="flex justify-between items-start mb-2">
          <div>
            <p className="text-sm text-gray-500">
              {formatDateTime(disagreement.commence_time)}
            </p>
            <p className="font-medium">
              {disagreement.away_team} @ {disagreement.home_team}
            </p>
          </div>
          <span className="text-lg font-bold text-orange-500">
            {disagreement.disagreement_pct.toFixed(1)}% spread
          </span>
        </div>
        <div className="text-sm text-gray-600">
          <span>
            Range: {formatProbability(disagreement.range.min_prob)} -{' '}
            {formatProbability(disagreement.range.max_prob)}
          </span>
        </div>
      </div>
    </Link>
  )
}
