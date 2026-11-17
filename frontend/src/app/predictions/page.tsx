import Link from 'next/link';
export default function PredictionsPage() {
  return <main className="max-w-xl mx-auto p-8 space-y-4"><h1 className="text-2xl font-semibold">Prédictions commerciales suspendues</h1><p>Ce module nécessite une méthode validée et des observations historiques suffisantes. Les analyses artistiques restent disponibles dans Discovery.</p><Link href="/discovery" className="underline">Ouvrir Discovery</Link></main>;
}
