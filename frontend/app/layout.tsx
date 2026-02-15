import type { Metadata } from 'next';
import { Playfair_Display } from 'next/font/google';
import { ReduxProvider } from '@/store/Provider';
import { Toaster } from 'react-hot-toast';
import AuthInitializer from '@/components/auth/AuthInitializer';
import './globals.css';

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Academe - AI Academic Assistant',
  description: 'Multi-agent AI assistant for academic learning',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={playfair.variable}>
      <body className="font-sans antialiased">
        <ReduxProvider>
          <AuthInitializer />
          {children}
          <Toaster position="top-right" />
        </ReduxProvider>
      </body>
    </html>
  );
}
