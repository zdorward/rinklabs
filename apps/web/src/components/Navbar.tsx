// apps/web/src/components/Navbar.tsx
'use client'

import Link from 'next/link'
import { UserButton, useUser } from '@clerk/nextjs'

export function Navbar() {
  const { isSignedIn } = useUser()

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="font-bold text-xl text-gray-900">
              Rinklabs
            </Link>
            <div className="flex space-x-4">
              <Link
                href="/"
                className="text-gray-600 hover:text-gray-900 px-3 py-2"
              >
                Markets
              </Link>
              <Link
                href="/pro"
                className="text-gray-600 hover:text-gray-900 px-3 py-2"
              >
                Pro
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {isSignedIn ? (
              <>
                <Link
                  href="/account"
                  className="text-gray-600 hover:text-gray-900"
                >
                  Account
                </Link>
                <UserButton afterSignOutUrl="/" />
              </>
            ) : (
              <Link
                href="/sign-in"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
