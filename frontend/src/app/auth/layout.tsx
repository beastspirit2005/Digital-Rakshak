import Link from "next/link";
import { Shield } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex bg-bg">
      {/* editorial panel — desktop only */}
      <div className="hidden lg:flex w-[42%] bg-surface-2 flex-col justify-between p-10">
        <Link href="/" className="flex items-center gap-2.5 w-fit">
          <Shield className="w-6 h-6 text-ink" strokeWidth={2.2} />
          <span className="font-display font-semibold text-base tracking-tight text-ink">
            Digital Rakshak
          </span>
        </Link>

        <div>
          <p className="font-serif italic text-ink-2 text-sm mb-4">Cyber threat intelligence</p>
          <h1 className="font-display font-semibold text-2xl leading-tight tracking-tight text-ink max-w-md">
            One report can take down an entire scam network.
          </h1>
          <p className="text-sm text-ink-2 mt-4 max-w-sm leading-relaxed">
            Every case you file is analyzed by eleven AI engines, linked against national
            intelligence, and routed to the officers who can act on it.
          </p>
        </div>

        <p className="text-xs text-ink-3">Ministry-grade security · Data stays in India</p>
      </div>

      {/* form column */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between p-6 lg:justify-end">
          <Link href="/" className="flex items-center gap-2 lg:hidden">
            <Shield className="w-5 h-5 text-ink" strokeWidth={2.2} />
            <span className="font-display font-semibold text-sm text-ink">Digital Rakshak</span>
          </Link>
          <ThemeToggle />
        </div>
        <div className="flex-1 flex items-start sm:items-center justify-center px-4 pb-12">
          <div className="w-full max-w-md">{children}</div>
        </div>
      </div>
    </div>
  );
}
