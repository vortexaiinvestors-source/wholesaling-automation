import './globals.css'

export const metadata = {
  title: 'VortexAI - AI-Powered Deal Finding Platform',
  description: 'Find undervalued assets 24/7 with AI-powered deal finding and buyer matching',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="bg-gray-50">{children}</body>
    </html>
  )
}
