// apps/web/src/components/MovementSparkline.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { api, OddsSnapshot } from '@/lib/api'

interface MovementSparklineProps {
  gameId: string
  homeTeam: string
}

export function MovementSparkline({ gameId, homeTeam }: MovementSparklineProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['odds-history', gameId],
    queryFn: () => api.getGameOddsHistory(gameId),
  })

  if (isLoading) {
    return (
      <div className="h-48 bg-gray-100 animate-pulse rounded-lg" />
    )
  }

  if (error || !data || data.snapshots.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-500 bg-gray-50 rounded-lg">
        No historical data available yet
      </div>
    )
  }

  const chartData = data.snapshots.map((snap: OddsSnapshot) => ({
    time: new Date(snap.timestamp).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    }),
    homeProb: Math.round(snap.consensus_home_prob * 1000) / 10,
    fullTime: new Date(snap.timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }),
  }))

  // Calculate min/max for better chart scaling
  const probs = chartData.map(d => d.homeProb)
  const minProb = Math.max(0, Math.min(...probs) - 5)
  const maxProb = Math.min(100, Math.max(...probs) + 5)

  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[minProb, maxProb]}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `${value}%`}
            width={45}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload
                return (
                  <div className="bg-white shadow-lg rounded-lg p-2 border text-sm">
                    <p className="text-gray-500">{data.fullTime}</p>
                    <p className="font-medium">
                      {homeTeam}: {data.homeProb}%
                    </p>
                  </div>
                )
              }
              return null
            }}
          />
          <ReferenceLine y={50} stroke="#e5e7eb" strokeDasharray="3 3" />
          <Line
            type="monotone"
            dataKey="homeProb"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#3b82f6' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
