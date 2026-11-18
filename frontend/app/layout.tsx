import type { ReactNode } from 'react';
export const metadata = { title: 'LemonTree Corp', description: 'AI startup workspace' };
export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="ko"><body style={{ margin: 0, fontFamily: 'system-ui, sans-serif', background: '#f7f8f4', color: '#173b30' }}>{children}</body></html>;
}
