'use client';

import { ForceLightMode } from './ForceLightMode';

export function LandingWrapper({ children }: { children: React.ReactNode }) {
  return <ForceLightMode>{children}</ForceLightMode>;
}
