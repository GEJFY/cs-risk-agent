import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Providers } from './providers'
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

export const metadata: Metadata = {
  title: 'CS Risk Agent',
  description: '連結子会社リスク分析ツール - Consolidated Subsidiary Risk Analysis Tool',
}

/**
 * ルートレイアウト
 * アプリケーション全体の構造を定義
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja" className={inter.variable}>
      <body className="dark min-h-screen bg-background font-sans antialiased">
        <Providers>
          <div className="flex min-h-screen">
            {/* サイドバーナビゲーション */}
            <Sidebar />

            {/* メインコンテンツエリア */}
            <div className="flex flex-1 flex-col">
              <Header />
              <main className="flex-1 p-6">
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  )
}
