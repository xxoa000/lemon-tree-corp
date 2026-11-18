import type { ReactNode } from 'react';
import './globals.css';

export const metadata = { title: 'LemonTree Corp', description: 'AI startup workspace' };

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
