// apps/web/src/app/page.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { api, DisagreementInfo } from '@/lib/api'
import { EdgeCard } from '@/components/EdgeCard'
import { formatDateTime, formatProbability } from '@/lib/utils'

function DisagreementCard({ disagreement }: { disagreement: DisagreementInfo }) {
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

export default function HomePage() {
  const {
    data: edgesData,
    isLoading: edgesLoading,
    error: edgesError,
  } = useQuery({
    queryKey: ['topEdges'],
    queryFn: () => api.getTopEdges(),
  })

  const {
    data: disagreementsData,
    isLoading: disagreementsLoading,
    error: disagreementsError,
  } = useQuery({
    queryKey: ['topDisagreements'],
    queryFn: () => api.getTopDisagreements(),
  })

  return (
    <div className="space-y-8">
      {/* Top Edges Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Top Edge Opportunities</h2>
          {edgesData?.truncated && (
            <Link
              href="/pro"
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              See all {edgesData.total_count} edges →
            </Link>
          )}
        </div>

        {edgesLoading && (
          <div className="text-center py-8 text-gray-500">Loading edges...</div>
        )}

        {edgesError && (
          <div className="text-center py-8 text-red-500">
            Failed to load edges. Please try again.
          </div>
        )}

        {edgesData && edgesData.edges.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No edge opportunities found today.
          </div>
        )}

        {edgesData && edgesData.edges.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {edgesData.edges.map((edge) => (
              <EdgeCard key={`${edge.game_id}-${edge.side}-${edge.bookmaker}`} edge={edge} />
            ))}
          </div>
        )}
      </section>

      {/* Top Disagreements Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Market Disagreements</h2>
          {disagreementsData?.truncated && (
            <Link
              href="/pro"
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              See all {disagreementsData.total_count} disagreements →
            </Link>
          )}
        </div>

        {disagreementsLoading && (
          <div className="text-center py-8 text-gray-500">
            Loading disagreements...
          </div>
        )}

        {disagreementsError && (
          <div className="text-center py-8 text-red-500">
            Failed to load disagreements. Please try again.
          </div>
        )}

        {disagreementsData && disagreementsData.disagreements.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No significant disagreements found today.
          </div>
        )}

        {disagreementsData && disagreementsData.disagreements.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {disagreementsData.disagreements.map((disagreement) => (
              <DisagreementCard
                key={disagreement.game_id}
                disagreement={disagreement}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
