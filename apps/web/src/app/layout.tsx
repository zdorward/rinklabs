// apps/web/src/app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs'
import { QueryProvider } from '@/components/QueryProvider'
import { Navbar } from '@/components/Navbar'
import './globals.css'

export const metadata = {
  title: 'Rinklabs - Hockey Market Intelligence',
  description: 'Market intelligence for NHL betting',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="bg-gray-50 min-h-screen">
          <QueryProvider>
            <Navbar />
            <main className="container mx-auto px-4 py-8">
              {children}
            </main>
          </QueryProvider>
        </body>
      </html>
    </ClerkProvider>
  )
}
