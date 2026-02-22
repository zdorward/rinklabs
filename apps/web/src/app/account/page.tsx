// apps/web/src/app/account/page.tsx
'use client'

import { useAuth, useUser } from '@clerk/nextjs'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'
import { Suspense } from 'react'

function AccountContent() {
  const { isSignedIn, isLoaded } = useUser()
  const { getToken } = useAuth()
  const searchParams = useSearchParams()
  const upgraded = searchParams.get('upgraded') === 'true'

  const { data: userInfo, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const token = await getToken()
      if (!token) throw new Error('No token')
      return api.getMe(token)
    },
    enabled: isSignedIn,
  })

  const handleUpgrade = async () => {
    try {
      const response = await fetch('/api/create-checkout-session', {
        method: 'POST',
      })
      const data = await response.json()
      if (data.url) {
        window.location.href = data.url
      }
    } catch (error) {
      console.error('Failed to create checkout session:', error)
    }
  }

  const handleManageBilling = async () => {
    try {
      const response = await fetch('/api/create-portal-session', {
        method: 'POST',
      })
      const data = await response.json()
      if (data.url) {
        window.location.href = data.url
      }
    } catch (error) {
      console.error('Failed to create portal session:', error)
    }
  }

  if (!isLoaded) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (!isSignedIn) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Sign in required</h2>
        <p className="text-gray-600">Please sign in to view your account.</p>
      </div>
    )
  }

  if (isLoading) {
    return <div className="text-center py-12">Loading account...</div>
  }

  const isPro = userInfo?.subscription_status === 'active'

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Account</h1>

      {upgraded && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <p className="text-green-800 font-medium">
            Welcome to Pro! Your subscription is now active.
          </p>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h2 className="text-xl font-semibold mb-4">Subscription Status</h2>

        <div className="space-y-4">
          <div className="flex justify-between items-center py-3 border-b">
            <span className="text-gray-600">Plan</span>
            <span className="font-medium">
              {isPro ? (
                <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                  Pro
                </span>
              ) : (
                <span className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm">
                  Free
                </span>
              )}
            </span>
          </div>

          {isPro && userInfo?.current_period_end && (
            <div className="flex justify-between items-center py-3 border-b">
              <span className="text-gray-600">Next billing date</span>
              <span className="font-medium">
                {new Date(userInfo.current_period_end).toLocaleDateString()}
              </span>
            </div>
          )}

          <div className="pt-4">
            {isPro ? (
              <button
                onClick={handleManageBilling}
                className="w-full bg-gray-100 text-gray-800 px-6 py-3 rounded-lg hover:bg-gray-200 font-medium"
              >
                Manage Billing
              </button>
            ) : (
              <button
                onClick={handleUpgrade}
                className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium"
              >
                Upgrade to Pro
              </button>
            )}
          </div>

          {!isPro && (
            <div className="bg-gray-50 rounded-lg p-4 mt-4">
              <h3 className="font-medium mb-2">Pro Benefits</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>- Unlimited edge opportunities</li>
                <li>- Full market disagreement analysis</li>
                <li>- Real-time odds updates</li>
                <li>- Priority support</li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AccountPage() {
  return (
    <Suspense fallback={<div className="text-center py-12">Loading...</div>}>
      <AccountContent />
    </Suspense>
  )
}
