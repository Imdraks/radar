'use client';

export function ForceLightMode({ children }: { children: React.ReactNode }) {
  // Only the root ThemeProvider owns the document theme during navigation.
  return (
    <div className="light" style={{ colorScheme: 'light' }}>
      {children}
    </div>
  );
}
