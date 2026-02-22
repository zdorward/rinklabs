// apps/web/src/components/LockedCard.tsx
import Link from 'next/link'

interface LockedCardProps {
  type: 'edge' | 'disagreement'
}

export function LockedCard({ type }: LockedCardProps) {
  return (
    <Link href="/pro">
      <div className="relative bg-white rounded-lg shadow-sm border p-4 overflow-hidden cursor-pointer group hover:shadow-md transition-shadow">
        {/* Blurred placeholder content */}
        <div className="blur-sm select-none pointer-events-none">
          <div className="flex justify-between items-start mb-2">
            <div>
              <p className="text-sm text-gray-500">Sat, Feb 28, 7:00 PM</p>
              <p className="font-medium">Team A @ Team B</p>
            </div>
            {type === 'edge' ? (
              <span className="text-lg font-bold text-green-500">+3.2% EV</span>
            ) : (
              <span className="text-lg font-bold text-amber-500">4.8%</span>
            )}
          </div>
          <div className="flex justify-between text-sm text-gray-600">
            {type === 'edge' ? (
              <>
                <span>Home ML</span>
                <span>bookmaker: +150</span>
              </>
            ) : (
              <>
                <span>Books disagree</span>
                <span>45% - 52%</span>
              </>
            )}
          </div>
        </div>

        {/* Lock overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-white via-white/80 to-transparent flex items-center justify-center">
          <div className="text-center">
            <div className="bg-blue-600 text-white rounded-full p-2 w-10 h-10 flex items-center justify-center mx-auto mb-2">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-900">Unlock with Pro</p>
          </div>
        </div>
      </div>
    </Link>
  )
}
