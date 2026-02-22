// apps/web/src/app/pro/page.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { EdgeCard } from '@/components/EdgeCard'
import { DisagreementCard } from '@/components/DisagreementCard'
import { SubscriptionGate } from '@/components/SubscriptionGate'

function ProContent() {
  const PRO_LIMIT = 100

  const {
    data: edgesData,
    isLoading: edgesLoading,
    error: edgesError,
  } = useQuery({
    queryKey: ['topEdges', 'pro'],
    queryFn: () => api.getTopEdges(PRO_LIMIT),
  })

  const {
    data: disagreementsData,
    isLoading: disagreementsLoading,
    error: disagreementsError,
  } = useQuery({
    queryKey: ['topDisagreements', 'pro'],
    queryFn: () => api.getTopDisagreements(PRO_LIMIT),
  })

  return (
    <div className="space-y-8">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg p-6 mb-8">
        <h1 className="text-3xl font-bold mb-2">Pro Market Intelligence</h1>
        <p className="text-blue-100">
          Unlimited access to all edge opportunities and market disagreements.
        </p>
      </div>

      {/* All Edges Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">All Edge Opportunities</h2>
          {edgesData && (
            <span className="text-gray-500">
              {edgesData.edges.length} of {edgesData.total_count} edges
            </span>
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

      {/* All Disagreements Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">All Market Disagreements</h2>
          {disagreementsData && (
            <span className="text-gray-500">
              {disagreementsData.disagreements.length} of{' '}
              {disagreementsData.total_count} disagreements
            </span>
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

export default function ProPage() {
  return (
    <SubscriptionGate>
      <ProContent />
    </SubscriptionGate>
  )
}
