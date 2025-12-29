import Link from 'next/link'
import { FileQuestion, Home } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="flex flex-col items-center gap-6 max-w-md text-center p-8">
        <div className="w-24 h-24 rounded-full bg-muted flex items-center justify-center">
          <FileQuestion className="w-12 h-12 text-muted-foreground" />
        </div>
        <div className="space-y-2">
          <h1 className="text-4xl font-bold">404</h1>
          <h2 className="text-xl font-semibold">Page introuvable</h2>
          <p className="text-muted-foreground">
            La page que vous recherchez n'existe pas ou a été déplacée.
          </p>
        </div>
        <Link 
          href="/dashboard" 
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <Home className="w-4 h-4" />
          Retour au tableau de bord
        </Link>
      </div>
    </div>
  )
}
