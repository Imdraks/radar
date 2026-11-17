'use client';
import { AppLayout, ProtectedRoute } from '@/components/layout';
import { LegacyToolsCatalog } from '@/components/product/LegacyTools';
export default function HistoricalToolsPage() {
  return <ProtectedRoute><AppLayout><LegacyToolsCatalog /></AppLayout></ProtectedRoute>;
}
