'use client'

import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw, Home } from 'lucide-react'
import Link from 'next/link'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body>
        <div className="flex items-center justify-center min-h-screen bg-background">
          <div className="flex flex-col items-center gap-6 max-w-md text-center p-8">
            <div className="w-20 h-20 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="w-10 h-10 text-destructive" />
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-bold">Erreur critique</h1>
              <p className="text-muted-foreground">
                Une erreur inattendue s'est produite. Nos équipes ont été notifiées.
              </p>
              {error.digest && (
                <p className="text-xs text-muted-foreground font-mono">
                  Code: {error.digest}
                </p>
              )}
            </div>
            <div className="flex gap-3">
              <Button onClick={reset} variant="outline" className="gap-2">
                <RefreshCw className="w-4 h-4" />
                Réessayer
              </Button>
              <Link href="/dashboard">
                <Button className="gap-2">
                  <Home className="w-4 h-4" />
                  Accueil
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </body>
    </html>
  )
}
