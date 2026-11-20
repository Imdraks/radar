import { RadarLoader } from '@/components/ui/radar-loader';

export default function Loading() {
  return <div className="flex min-h-[60vh] items-center justify-center bg-background p-8"><RadarLoader label="Chargement des prospects…" /></div>;
}
