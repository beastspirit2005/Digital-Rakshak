import type { Metadata } from "next";
import { Archivo, Instrument_Sans, Fraunces } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
  preload: true,
});

const instrumentSans = Instrument_Sans({
  variable: "--font-instrument",
  subsets: ["latin"],
  display: "swap",
  preload: true,
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
  display: "swap",
  preload: true,
});

export const metadata: Metadata = {
  title: "Digital Rakshak | National Cyber Defense",
  description: "AI-powered sovereign cyber threat intelligence for a safer digital India",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/brand/logo-shield-32.png", type: "image/png", sizes: "32x32" },
      { url: "/brand/logo-shield.png", type: "image/png", sizes: "512x512" },
    ],
    shortcut: "/favicon.ico",
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  openGraph: {
    title: "Digital Rakshak | National Cyber Defense",
    description: "AI-powered sovereign cyber threat intelligence for a safer digital India",
    url: "https://digitalrakshak.in",
    siteName: "Digital Rakshak",
    images: [
      {
        url: "/brand/og-image.png",
        width: 1200,
        height: 630,
        alt: "Digital Rakshak Sovereign Cyber Defense",
      },
    ],
    locale: "en_IN",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Digital Rakshak | National Cyber Defense",
    description: "AI-powered sovereign cyber threat intelligence for a safer digital India",
    images: ["/brand/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${archivo.variable} ${instrumentSans.variable} ${fraunces.variable} antialiased min-h-screen flex flex-col`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
