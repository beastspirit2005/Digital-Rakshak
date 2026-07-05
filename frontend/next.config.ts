import type { NextConfig } from "next";

const externalBackend = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const proxyTarget = process.env.API_PROXY_TARGET?.replace(/\/$/, "") || externalBackend || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const isVercel = process.env.VERCEL === "1" || !!process.env.VERCEL_URL || !!process.env.VERCEL_ENV;
    if (isVercel && !externalBackend && !process.env.API_PROXY_TARGET) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${proxyTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
