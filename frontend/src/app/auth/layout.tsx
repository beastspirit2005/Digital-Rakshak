import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";
import { BrandIdentity } from "@/components/brand-identity";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-bg relative flex flex-col">
      {/* Top brand header */}
      <header className="w-full flex items-center justify-between px-6 md:px-10 py-6">
        <Link href="/" className="w-fit">
          <BrandIdentity />
        </Link>

        <ThemeToggle />
      </header>

      {/* Centered auth form */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 pb-20">
        <div className="w-full max-w-md">
          {children}
        </div>
      </main>
    </div>
  );
}