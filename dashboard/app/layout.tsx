import type { Metadata } from 'next'
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
import './globals.css'

export const metadata: Metadata = {
  title: 'Brain',
  description: 'Brain — Autonomous Agent System',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`} data-theme="dark">
      <body className="font-mono antialiased">
        {children}
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            var saved = localStorage.getItem('brain-theme') || 'dark';
            document.documentElement.setAttribute('data-theme', saved);
          })();
        `}} />
      </body>
    </html>
  )
}
