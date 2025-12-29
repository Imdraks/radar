import Link from 'next/link'
import { FileQuestion, ArrowLeft } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="flex flex-col items-center gap-6 max-w-md text-center p-8">
        <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center">
          <FileQuestion className="w-10 h-10 text-muted-foreground" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold">Lead introuvable</h2>
          <p className="text-muted-foreground">
            Ce lead n'existe pas ou a été supprimé.
          </p>
        </div>
        <Link 
          href="/leads" 
          className="inline-flex items-center gap-2 text-primary hover:underline"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour aux leads
        </Link>
      </div>
    </div>
  )
}
