// apps/web/src/components/Navbar.tsx
import Link from 'next/link'
import {
  SignInButton,
  SignedIn,
  SignedOut,
  UserButton,
} from '@clerk/nextjs'

export function Navbar() {
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
            <SignedOut>
              <SignInButton>
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                  Sign In
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/account"
                className="text-gray-600 hover:text-gray-900"
              >
                Account
              </Link>
              <UserButton />
            </SignedIn>
          </div>
        </div>
      </div>
    </nav>
  )
}
