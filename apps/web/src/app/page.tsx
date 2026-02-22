// apps/web/src/app/page.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { api } from '@/lib/api'
import { EdgeCard } from '@/components/EdgeCard'
import { DisagreementCard } from '@/components/DisagreementCard'
import { LockedCard } from '@/components/LockedCard'

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
            <span className="text-sm text-gray-500">
              Showing {edgesData.edges.length} of {edgesData.total_count}
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
            {edgesData.truncated &&
              Array.from({ length: Math.min(3, edgesData.total_count - edgesData.edges.length) }).map((_, i) => (
                <LockedCard key={`locked-edge-${i}`} type="edge" />
              ))
            }
          </div>
        )}

        {edgesData?.truncated && (
          <div className="mt-4 text-center">
            <Link
              href="/pro"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Unlock {edgesData.total_count - edgesData.edges.length} more edges
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </Link>
          </div>
        )}
      </section>

      {/* Top Disagreements Section */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Market Disagreements</h2>
          {disagreementsData?.truncated && (
            <span className="text-sm text-gray-500">
              Showing {disagreementsData.disagreements.length} of {disagreementsData.total_count}
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
            {disagreementsData.truncated &&
              Array.from({ length: Math.min(3, disagreementsData.total_count - disagreementsData.disagreements.length) }).map((_, i) => (
                <LockedCard key={`locked-disagreement-${i}`} type="disagreement" />
              ))
            }
          </div>
        )}

        {disagreementsData?.truncated && (
          <div className="mt-4 text-center">
            <Link
              href="/pro"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Unlock {disagreementsData.total_count - disagreementsData.disagreements.length} more disagreements
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </Link>
          </div>
        )}
      </section>
    </div>
  )
}
