// apps/web/src/app/games/[gameId]/page.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'
import { formatDateTime, formatProbability } from '@/lib/utils'
import { OddsTable } from '@/components/OddsTable'

export default function GamePage() {
  const params = useParams()
  const gameId = params.gameId as string

  const { data: game, isLoading, error } = useQuery({
    queryKey: ['game', gameId],
    queryFn: () => api.getGame(gameId),
  })

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-8"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error || !game) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Link href="/" className="text-blue-600 hover:underline mb-4 inline-block">
          &larr; Back to games
        </Link>
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">
          Game not found or error loading data.
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link href="/" className="text-blue-600 hover:underline mb-4 inline-block">
        &larr; Back to games
      </Link>

      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <p className="text-sm text-gray-500 mb-1">
          {formatDateTime(game.commence_time)}
        </p>
        <h1 className="text-2xl font-bold mb-4">
          {game.away_team} @ {game.home_team}
        </h1>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Home Consensus</p>
            <p className="text-xl font-bold">
              {formatProbability(game.consensus.home_prob)}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Away Consensus</p>
            <p className="text-xl font-bold">
              {formatProbability(game.consensus.away_prob)}
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Disagreement</p>
            <p className="text-xl font-bold">
              {game.disagreement.toFixed(1)}%
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Books</p>
            <p className="text-xl font-bold">
              {game.odds_by_book.length}
            </p>
          </div>
        </div>

        {game.movement.change_from_open !== null && (
          <div className="bg-blue-50 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-700 font-medium">Line Movement</p>
            <div className="flex gap-4 mt-2">
              {game.movement.home_open !== null && (
                <span className="text-sm">
                  Open: {formatProbability(game.movement.home_open)}
                </span>
              )}
              <span className="text-sm">
                Current: {formatProbability(game.movement.home_current)}
              </span>
              <span className={`text-sm font-medium ${
                game.movement.change_from_open! > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {game.movement.change_from_open! > 0 ? '+' : ''}
                {game.movement.change_from_open!.toFixed(1)}pp from open
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h2 className="text-lg font-semibold mb-4">Odds by Bookmaker</h2>
        <OddsTable
          odds={game.odds_by_book}
          homeTeam={game.home_team}
          awayTeam={game.away_team}
        />
      </div>
    </div>
  )
}
