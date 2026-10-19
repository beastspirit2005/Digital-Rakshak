import type { NextConfig } from "next";

const externalBackend = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const proxyTarget = process.env.API_PROXY_TARGET?.replace(/\/$/, "") || externalBackend || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  compress: true,
  poweredByHeader: false,
  compiler: {
    removeConsole: process.env.NODE_ENV === "production" ? { exclude: ["error", "warn"] } : false,
  },
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 86400,
  },
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "recharts",
      "framer-motion",
      "@supabase/supabase-js",
      "clsx",
      "tailwind-merge",
      "zod",
      "@hookform/resolvers",
    ],
  },
  async headers() {
    return [
      {
        source: "/:all*(svg|jpg|png|webp|avif|ico|woff|woff2)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      {
        source: "/:path*",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },
  async rewrites() {
    const isVercel = process.env.VERCEL === "1" || !!process.env.VERCEL_URL || !!process.env.VERCEL_ENV;
    // On Vercel, NEVER rewrite — experimental services handle /api routing
    if (isVercel) return [];
    return [
      {
        source: "/api/v1/:path*",
        destination: `${proxyTarget}/v1/:path*`, // Proxy to backend (supports docker network & localhost)
      },
    ];
  },
};

export default nextConfig;
