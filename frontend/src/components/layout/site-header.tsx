"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  ShieldCheck, 
  Menu, 
  X, 
  ArrowRight, 
  Sparkles, 
  Building2, 
  HelpCircle, 
  Info, 
  Mail, 
  ScanSearch,
  ExternalLink
} from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuthStore } from "@/lib/auth-store";

export function SiteHeader() {
  const pathname = usePathname();
  const { isAuthenticated, user, isHydrated, hydrate } = useAuthStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (!isHydrated) {
      hydrate();
    }
  }, [hydrate, isHydrated]);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  const getDashboardHref = () => {
    if (!user) return "/personal";
    switch (user.role) {
      case "admin":
        return "/admin";
      case "police":
      case "cyber_cell":
        return "/police";
      case "banker":
      case "bank_employee":
        return "/banker/transactions";
      default:
        return "/personal";
    }
  };

  const navLinks = [
    { label: "Prevention", href: "/prevention", icon: ScanSearch },
    { label: "Personal Shield", href: "/personal", icon: ShieldCheck },
    { label: "Business API", href: "/business", icon: Building2 },
    { label: "About", href: "/about", icon: Info },
    { label: "FAQ", href: "/faq", icon: HelpCircle },
    { label: "Contact", href: "/contact", icon: Mail },
  ];

  const isCurrent = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-[#0a0a0c]/95 dark:bg-[#0a0a0c]/95 backdrop-blur-md border-b border-white/8 text-[#E7EEF3]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand Logo & Title */}
        <Link 
          href="/" 
          className="flex items-center gap-3 min-w-0 transition-opacity hover:opacity-90 group"
          aria-label="Digital Rakshak Home"
        >
          <div className="flex items-center justify-center shrink-0 w-9 h-9 rounded-lg bg-[#18181c] border border-white/10 group-hover:border-[#F59E0B]/40 transition-colors">
            <BrandLogo size={24} />
          </div>
          <div className="min-w-0 flex flex-col">
            <span className="font-display font-bold text-base sm:text-lg tracking-tight leading-none text-white flex items-center gap-1.5">
              Digital Rakshak
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#138808] animate-pulse" title="System Operational" />
            </span>
            <span className="text-[10px] uppercase font-mono tracking-wider text-[#A7B4BD]">
              National Cyber Defense
            </span>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 lg:gap-2">
          {navLinks.map((item) => {
            const active = isCurrent(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all duration-150 ${
                  active
                    ? "bg-[#18181c] text-[#F59E0B] border border-[#F59E0B]/30 shadow-sm"
                    : "text-[#A7B4BD] hover:text-white hover:bg-white/5"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Action Controls & Auth */}
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />

          {mounted && isAuthenticated ? (
            <Link
              href={getDashboardHref()}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#F59E0B] hover:bg-[#D97706] text-[#08131A] text-xs font-bold transition-all shadow-sm active:scale-95"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#08131A]" />
              <span>Console</span>
            </Link>
          ) : (
            <div className="hidden sm:flex items-center gap-2">
              <Link
                href="/auth/login"
                className="px-3 py-1.5 rounded-lg text-xs font-semibold text-[#A7B4BD] hover:text-white hover:bg-white/5 transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="/auth/register"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F59E0B] hover:bg-[#D97706] text-[#08131A] text-xs font-bold transition-all shadow-sm active:scale-95"
              >
                <span>Protect Now</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          )}

          {/* Mobile Menu Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden inline-flex items-center justify-center p-2 rounded-lg text-[#A7B4BD] hover:text-white hover:bg-white/5 transition-colors"
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-white/10 bg-[#0a0a0c] px-4 pt-3 pb-6 space-y-3">
          <nav className="flex flex-col space-y-1">
            {navLinks.map((item) => {
              const active = isCurrent(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? "bg-[#18181c] text-[#F59E0B] border border-[#F59E0B]/30"
                      : "text-[#A7B4BD] hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0 text-[#F59E0B]" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="pt-3 border-t border-white/10 flex flex-col gap-2">
            {mounted && isAuthenticated ? (
              <Link
                href={getDashboardHref()}
                className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-[#F59E0B] text-[#08131A] text-sm font-bold shadow-sm"
              >
                <Sparkles className="w-4 h-4" />
                <span>Open Dashboard Console</span>
              </Link>
            ) : (
              <>
                <Link
                  href="/auth/login"
                  className="w-full text-center py-2.5 rounded-lg bg-[#18181c] border border-white/10 text-white text-sm font-medium"
                >
                  Sign in
                </Link>
                <Link
                  href="/auth/register"
                  className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-[#F59E0B] text-[#08131A] text-sm font-bold shadow-sm"
                >
                  <span>Create Free Account</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </>
            )}

            <div className="pt-2 text-center">
              <span className="text-[11px] text-[#64748B]">
                Immediate fraud emergency? Call national helpline{" "}
                <a href="tel:1930" className="text-[#F59E0B] font-bold hover:underline">
                  1930
                </a>
              </span>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
