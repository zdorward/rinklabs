// apps/web/src/components/SubscriptionGate.tsx
'use client'

import { useUser } from '@clerk/nextjs'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import Link from 'next/link'

interface SubscriptionGateProps {
  children: React.ReactNode
}

export function SubscriptionGate({ children }: SubscriptionGateProps) {
  const { isSignedIn, user } = useUser()

  const { data: userInfo, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      // Get token from Clerk - simplified for MVP
      return api.getMe('')
    },
    enabled: isSignedIn,
  })

  if (!isSignedIn) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Sign in required</h2>
        <p className="text-gray-600 mb-6">
          Sign in to access Pro features
        </p>
        <Link
          href="/sign-in"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
        >
          Sign In
        </Link>
      </div>
    )
  }

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (userInfo?.subscription_status !== 'active') {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Upgrade to Pro</h2>
        <p className="text-gray-600 mb-6">
          Get unlimited access to all market intelligence
        </p>
        <Link
          href="/account"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
        >
          Upgrade Now
        </Link>
      </div>
    )
  }

  return <>{children}</>
}
