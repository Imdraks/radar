import Link from 'next/link';
export default function GuideNotFound() {
  return <div className="rounded-2xl border bg-white p-8"><h1 className="text-2xl font-semibold">Ce guide n’existe pas.</h1><p className="mt-3 text-muted-foreground">Retrouvez le sujet depuis le sommaire ou recherchez un autre terme.</p><Link href="/doc" className="mt-5 inline-block text-primary underline">Retour à la documentation</Link></div>;
}
