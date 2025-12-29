'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('Dossiers error:', error)
  }, [error])

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="flex flex-col items-center gap-6 max-w-md text-center p-8">
        <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
          <AlertCircle className="w-8 h-8 text-destructive" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold">Erreur de chargement</h2>
          <p className="text-muted-foreground">
            {error.message || "Impossible de charger les dossiers."}
          </p>
        </div>
        <Button onClick={reset} variant="outline" className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Réessayer
        </Button>
      </div>
    </div>
  )
}
