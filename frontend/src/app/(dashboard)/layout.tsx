"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Shield,
  Activity,
  Map,
  FileText,
  Settings,
  LogOut,
  Bell,
  Search,
  ShieldAlert,
  Users,
  CheckSquare,
  Network,
  ShieldCheck,
  Building,
  Siren,
  UserCircle,
  Bot,
  MoreHorizontal,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuthStore } from "@/lib/auth-store";
import { ThemeToggle } from "@/components/theme-toggle";
import { GlobalChatWidget } from "@/components/global-chat-widget";
import { ToastProvider } from "@/components/ui/toast";
import { Avatar } from "@/components/ui/avatar";

const adminSections = [
  {
    label: "Admin",
    items: [
      { name: "Admin dashboard", short: "Admin", href: "/admin", icon: Activity },
      { name: "Users", short: "Users", href: "/admin/users", icon: Users },
      { name: "Approvals", short: "Approvals", href: "/admin/approvals", icon: CheckSquare },
      { name: "National analytics", short: "Analytics", href: "/admin/intelligence", icon: Network },
      { name: "AI health", short: "AI health", href: "/admin/ai-health", icon: Bot },
      { name: "Platform settings", short: "Settings", href: "/admin/settings", icon: Settings },
    ],
  },
  {
    label: "Investigation",
    items: [
      { name: "Workbench", short: "Workbench", href: "/workbench", icon: Siren },
      { name: "Case register", short: "Cases", href: "/workbench/reports", icon: FileText },
      { name: "Spatial map", short: "Map", href: "/workbench/map", icon: Map },
      { name: "Graph explorer", short: "Graph", href: "/workbench/graph", icon: Network },
      { name: "AI co-pilot", short: "Co-pilot", href: "/copilot", icon: Bot },
    ],
  },
  {
    label: "Nodal desk",
    items: [
      { name: "Nodal dashboard", short: "Desk", href: "/banker", icon: Building },
      { name: "Report a scam", short: "Report", href: "/report", icon: ShieldAlert },
      { name: "Prevention", short: "Prevent", href: "/prevention", icon: ShieldCheck },
      { name: "Spatial map", short: "Map", href: "/workbench/map", icon: Map },
    ],
  },
  {
    label: "Citizen",
    items: [
      { name: "My reports", short: "Reports", href: "/citizen", icon: UserCircle },
      { name: "Report a scam", short: "Report", href: "/report", icon: ShieldAlert },
      { name: "Prevention", short: "Prevent", href: "/prevention", icon: ShieldCheck },
      { name: "Spatial map", short: "Map", href: "/workbench/map", icon: Map },
    ],
  },
];

type NavItem = (typeof adminSections)[number]["items"][number];

function NavLink({
  item,
  active,
  onClick,
}: {
  item: NavItem;
  active: boolean;
  onClick?: () => void;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onClick}
      className={cn(
        "relative flex items-center gap-3 px-3 py-2 rounded-control text-sm transition-colors duration-150",
        active
          ? "bg-surface text-ink font-medium shadow-card"
          : "text-ink-2 hover:text-ink hover:bg-surface/60"
      )}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-0.5 rounded-pill bg-accent" />
      )}
      <Icon className="w-4 h-4 shrink-0" strokeWidth={active ? 2.2 : 2} />
      {item.name}
    </Link>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { logout, user } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/auth/login");
  };

  // Section detection and role gating — unchanged behavior.
  const isAdminSection = pathname.startsWith("/admin");
  const isCitizenSection = pathname.startsWith("/citizen");
  const isWorkbenchMap = pathname === "/workbench/map";
  const isWorkbenchSection = pathname.startsWith("/workbench") && !isWorkbenchMap;

  let allowedRoles: string[] | undefined = undefined;
  if (isAdminSection) {
    allowedRoles = ["admin"];
  } else if (isWorkbenchMap) {
    allowedRoles = ["admin", "police", "cyber_cell", "bank_employee", "banker", "citizen"];
  } else if (isWorkbenchSection) {
    allowedRoles = ["admin", "police", "cyber_cell", "bank_employee", "banker"];
  } else if (pathname.startsWith("/banker")) {
    allowedRoles = ["admin", "bank_employee", "banker"];
  } else if (isCitizenSection) {
    allowedRoles = ["admin", "citizen"];
  } else if (pathname.startsWith("/report") || pathname.startsWith("/prevention")) {
    allowedRoles = ["admin", "citizen", "police", "cyber_cell", "bank_employee", "banker"];
  } else if (pathname.startsWith("/copilot")) {
    allowedRoles = ["admin", "police", "cyber_cell"];
  }

  let sections: typeof adminSections = [];
  if (user?.role === "admin") {
    sections = adminSections;
  } else if (user?.role === "police" || user?.role === "cyber_cell") {
    sections = adminSections.filter((s) => s.label === "Investigation");
  } else if (user?.role === "banker" || user?.role === "bank_employee") {
    sections = adminSections.filter((s) => s.label === "Nodal desk");
  } else if (user?.role === "citizen") {
    sections = adminSections.filter((s) => s.label === "Citizen");
  }

  const flatNav = sections.flatMap((s) => s.items);
  // Mobile tab bar: first three destinations plus "More".
  const tabItems = flatNav
    .filter((item, i, arr) => arr.findIndex((x) => x.href === item.href) === i)
    .slice(0, 3);

  const isActive = (href: string) => pathname === href;

  const sidebarContent = (
    <>
      <div className="h-16 flex items-center gap-2.5 px-5">
        <Shield className="w-6 h-6 text-ink" strokeWidth={2.2} />
        <span className="font-display font-semibold text-base tracking-tight text-ink">
          Digital Rakshak
        </span>
      </div>

      <nav className="px-3 pb-4 flex-1 overflow-y-auto space-y-6">
        {sections.map((section) => (
          <div key={section.label}>
            {sections.length > 1 && (
              <p className="px-3 mb-1.5 text-xs text-ink-3">{section.label}</p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={`${section.label}-${item.href}`}
                  item={item}
                  active={isActive(item.href)}
                  onClick={() => setSidebarOpen(false)}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-3">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-control text-sm text-ink-2 hover:text-danger hover:bg-danger-tint transition-colors duration-150"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <ProtectedRoute allowedRoles={allowedRoles}>
      <ToastProvider>
        <div className="min-h-screen bg-bg flex">
          {/* desktop sidebar */}
          <aside className="hidden md:flex w-60 shrink-0 flex-col bg-surface-2 sticky top-0 h-screen">
            {sidebarContent}
          </aside>

          {/* mobile slide-in */}
          <div
            className={cn(
              "fixed inset-0 z-50 md:hidden transition-[visibility]",
              sidebarOpen ? "visible" : "invisible delay-300"
            )}
          >
            <div
              className={cn(
                "absolute inset-0 bg-ink/40 transition-opacity duration-300",
                sidebarOpen ? "opacity-100" : "opacity-0"
              )}
              onClick={() => setSidebarOpen(false)}
            />
            <aside
              className={cn(
                "absolute inset-y-0 left-0 w-72 max-w-[85vw] flex flex-col bg-surface-2 transition-transform duration-300 ease-out",
                sidebarOpen ? "translate-x-0" : "-translate-x-full"
              )}
            >
              <button
                onClick={() => setSidebarOpen(false)}
                aria-label="Close menu"
                className="absolute top-4 right-4 p-2 rounded-pill text-ink-3 hover:text-ink hover:bg-surface transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
              {sidebarContent}
            </aside>
          </div>

          {/* main column */}
          <div className="flex-1 flex flex-col min-w-0">
            <header className="h-16 flex items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
              <div className="flex items-center gap-2.5 md:hidden">
                <Shield className="w-5 h-5 text-ink" strokeWidth={2.2} />
                <span className="font-display font-semibold text-sm text-ink">Digital Rakshak</span>
              </div>

              <div className="hidden md:block relative w-full max-w-sm">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-3" />
                <input
                  type="search"
                  placeholder="Search cases, numbers, domains"
                  className="w-full h-10 pl-10 pr-4 bg-surface rounded-pill text-sm text-ink placeholder:text-ink-3 border border-transparent hover:border-line focus:border-accent-text focus:outline-none transition-colors"
                />
              </div>

              <div className="flex items-center gap-1.5">
                <ThemeToggle />
                <button
                  aria-label="Notifications"
                  className="relative p-2 text-ink-2 hover:text-ink rounded-pill hover:bg-surface-2 transition-colors duration-150"
                >
                  <Bell className="w-4 h-4" />
                </button>
                <div className="flex items-center gap-2.5 pl-2">
                  <Avatar name={user?.full_name || user?.email} size="sm" />
                  <span className="hidden lg:block text-sm text-ink-2 max-w-[12rem] truncate">
                    {user?.full_name || user?.email}
                  </span>
                </div>
              </div>
            </header>

            <main className="flex-1 px-4 sm:px-6 lg:px-8 pb-24 md:pb-10">
              <div className="max-w-6xl mx-auto w-full">{children}</div>
            </main>
          </div>

          {/* mobile bottom tab bar */}
          <nav className="fixed md:hidden bottom-0 inset-x-0 z-40 bg-surface border-t border-line pb-[env(safe-area-inset-bottom)]">
            <div className="flex">
              {tabItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex-1 flex flex-col items-center justify-center gap-1 min-h-14 text-xs transition-colors duration-150",
                      active ? "text-ink font-medium" : "text-ink-3"
                    )}
                  >
                    <Icon className="w-5 h-5" strokeWidth={active ? 2.2 : 2} />
                    {item.short}
                    {active && <span className="absolute top-0 h-0.5 w-8 rounded-pill bg-accent" />}
                  </Link>
                );
              })}
              <button
                onClick={() => setSidebarOpen(true)}
                className="flex-1 flex flex-col items-center justify-center gap-1 min-h-14 text-xs text-ink-3"
              >
                <MoreHorizontal className="w-5 h-5" />
                More
              </button>
            </div>
          </nav>

          <GlobalChatWidget />
        </div>
      </ToastProvider>
    </ProtectedRoute>
  );
}
