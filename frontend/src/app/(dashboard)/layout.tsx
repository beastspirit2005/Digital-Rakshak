"use client";
import { useMemo, useState } from "react";
import { ProtectedRoute } from "@/components/protected-route";
import type { UserRole } from "@/lib/auth-store";
import Link from "next/link";
import { BrandLogo } from "@/components/brand-logo";
import { usePathname, useRouter } from "next/navigation";

import {
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
  LifeBuoy,
  MoreHorizontal,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

import { useAuthStore } from "@/lib/auth-store";
import { ThemeToggle } from "@/components/theme-toggle";
import { GlobalChatWidget } from "@/components/global-chat-widget";
import { ToastProvider } from "@/components/ui/toast";
import { Avatar } from "@/components/ui/avatar";
import { useSessionTimeout } from "@/hooks/use-session-timeout";

const adminSections = [
  {
    label: "Admin",
    items: [
      { name: "Admin dashboard", short: "Admin", href: "/admin", icon: Activity },
      { name: "Users", short: "Users", href: "/admin/users", icon: Users },
      { name: "Reports", short: "Reports", href: "/admin/reports", icon: FileText },
      { name: "Approvals", short: "Approvals", href: "/admin/approvals", icon: CheckSquare },
      { name: "National analytics", short: "Analytics", href: "/admin/intelligence", icon: Network },
      { name: "AI health", short: "AI health", href: "/admin/ai-health", icon: Bot },
      { name: "Platform settings", short: "Settings", href: "/admin/settings", icon: Settings },
      { name: "Support tickets", short: "Support", href: "/admin/support", icon: LifeBuoy },
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
      { name: "Help & support", short: "Help", href: "/help", icon: LifeBuoy },
    ],
  },
  {
    label: "Nodal desk",
    items: [
      { name: "Nodal dashboard", short: "Desk", href: "/banker", icon: Building },
      { name: "Report a scam", short: "Report", href: "/report", icon: ShieldAlert },
      { name: "Prevention", short: "Prevent", href: "/prevention", icon: ShieldCheck },
      { name: "Spatial map", short: "Map", href: "/workbench/map", icon: Map },
      { name: "Help & support", short: "Help", href: "/help", icon: LifeBuoy },
    ],
  },
  {
    label: "Citizen",
    items: [
      { name: "My reports", short: "Reports", href: "/citizen", icon: UserCircle },
      { name: "Report a scam", short: "Report", href: "/report", icon: ShieldAlert },
      { name: "Prevention", short: "Prevent", href: "/prevention", icon: ShieldCheck },
      
      { name: "Help & support", short: "Help", href: "/help", icon: LifeBuoy },
    ],
  },
];
const sectionsForRole = (role: UserRole) => {
  if (role === "admin") {
    return adminSections;
  }

  if (role === "police" || role === "cyber_cell") {
    return adminSections.filter(
      (section) => section.label === "Investigation"
    );
  }

  if (role === "banker" || role === "bank_employee") {
    return adminSections.filter(
      (section) => section.label === "Nodal desk"
    );
  }

  if (role === "citizen") {
    return adminSections.filter(
      (section) => section.label === "Citizen"
    );
  }

  return [];
};
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
        "relative flex items-center gap-3.5 px-3.5 py-2.5 rounded-control text-[15px] transition-colors duration-150",
        active
          ? "bg-surface-3/40 text-accent-text font-semibold shadow-[inset_1px_1px_0px_rgba(255,255,255,0.05)] border-l-2 border-accent"
          : "text-ink-2 hover:text-ink hover:bg-surface-3/20 font-medium"
      )}
    >
      <Icon className={cn("w-5 h-5 shrink-0 transition-transform duration-150 active:scale-95", active ? "text-accent-text" : "text-ink-3")} strokeWidth={active ? 2.2 : 2} />
      {item.name}
    </Link>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  useSessionTimeout();
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { logout, user } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/auth/login");
  };

  const isAdminSection = pathname.startsWith("/admin");
  const isCitizenSection = pathname.startsWith("/citizen");
  const isWorkbenchMap = pathname === "/workbench/map";
  const isWorkbenchSection = pathname.startsWith("/workbench") && !isWorkbenchMap;
const brandSubtitle = (() => {
  if (!user) {
    return "Secure Access";
  }

  if (user.role === "admin") {
    return "Platform Command";
  }

  if (
    user.role === "police" ||
    user.role === "cyber_cell"
  ) {
    return "Threat Command";
  }

  if (
    user.role === "banker" ||
    user.role === "bank_employee"
  ) {
    return "Financial Safety";
  }

  if (user.role === "citizen") {
    return "Citizen Protection";
  }

  return "Secure Access";
})();
 let allowedRoles: UserRole[] | undefined;

if (pathname.startsWith("/admin")) {
  allowedRoles = ["admin"];
} else if (
  pathname.startsWith("/workbench") ||
  pathname.startsWith("/copilot") ||
  pathname.startsWith("/police")
) {
  allowedRoles = ["admin", "police", "cyber_cell"];
} else if (pathname.startsWith("/banker")) {
  allowedRoles = ["admin", "banker", "bank_employee"];
} else if (pathname.startsWith("/citizen")) {
  allowedRoles = ["admin", "citizen"];
} else if (
  pathname.startsWith("/report") ||
  pathname.startsWith("/prevention") ||
  pathname.startsWith("/help")
) {
  allowedRoles = [
    "admin",
    "citizen",
    "police",
    "cyber_cell",
    "banker",
    "bank_employee",
  ];
}
const sections = useMemo(() => {
  if (!user) return [];

  return sectionsForRole(user.role);
}, [user]);

  const flatNav = sections.flatMap((s) => s.items);
  const tabItems = flatNav
    .filter((item, i, arr) => arr.findIndex((x) => x.href === item.href) === i)
    .slice(0, 3);

  const isActive = (href: string) => pathname === href;

const sidebarContent = (
  <>
    {/* Digital Rakshak branding */}
    <Link
      href="/"
      className="flex items-center gap-3 px-4 pt-5 pb-5 border-b border-line/15"
      onClick={() => setSidebarOpen(false)}
    >
      <div className="w-12 h-12 rounded-2xl bg-[#111f27] border border-[#253540] flex items-center justify-center shrink-0">
        <BrandLogo size={28} />
      </div>

      <div className="min-w-0">
        <h1 className="font-display font-bold text-lg text-ink tracking-tight whitespace-nowrap">
          Digital Rakshak
        </h1>

        <p className="text-[9px] text-accent-text tracking-[0.22em] uppercase mt-1 whitespace-nowrap">
  {brandSubtitle}
</p>
      </div>
    </Link>

    <nav className="px-3.5 py-6 flex-1 overflow-y-auto space-y-8">
        {sections.map((section) => (
          <div key={section.label} className="space-y-2.5">
            {sections.length > 1 && (
              <p className="px-3.5 text-[11px] font-bold uppercase tracking-[0.16em] text-[#557094]">
                {section.label}
              </p>
            )}
            <div className="space-y-1">
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

      <div className="p-3.5 border-t border-line/10 bg-surface-2/40">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-control text-[15px] font-semibold text-[#fb5b5b]/90 hover:text-[#fb5b5b] hover:bg-[#fb5b5b]/10 border border-transparent hover:border-[#fb5b5b]/25 transition-all duration-150"
        >
          <LogOut className="w-5 h-5" />
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
          <aside className="hidden md:flex w-60 shrink-0 flex-col bg-surface-2 sticky top-0 h-screen border-r border-line/15 shadow-xl">
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
                "absolute inset-0 bg-ink/40 transition-opacity duration-300 backdrop-blur-sm",
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
                className="absolute top-5 right-5 p-2 rounded-pill text-ink-3 hover:text-ink hover:bg-surface transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
              {sidebarContent}
            </aside>
          </div>

          {/* main column */}
          <div className="flex-1 flex flex-col min-w-0">
            <header className="h-20 flex items-center justify-end gap-4 px-4 sm:px-6 lg:px-8 border-b border-line/10 bg-bg/80 backdrop-blur-md sticky top-0 z-30">
             

              <div className="hidden md:block relative w-full max-w-sm">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-ink-3" />
                <input
                  type="search"
                  placeholder="Search cases, phone numbers, UPI IDs, domains..."
                  className="w-full h-11 pl-11 pr-12 bg-surface-2/60 hover:bg-surface-2 rounded-control text-[15px] text-ink placeholder:text-ink-3 border border-line/10 hover:border-line/30 focus:border-accent focus:bg-surface focus:outline-none transition-all"
                />
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-line/40 text-ink-3 pointer-events-none">
                  ⌘K
                </span>
              </div>

              <div className="flex items-center gap-2">
                <ThemeToggle />
                <button
                  aria-label="Notifications"
                  className="relative p-2.5 text-ink-2 hover:text-ink rounded-pill hover:bg-surface-2/60 transition-colors duration-150"
                >
                  <Bell className="w-5 h-5" />
                  <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-danger ring-2 ring-surface" />
                </button>
                <div className="flex items-center gap-3 pl-2.5 border-l border-line/10">
                  <Avatar name={user?.full_name || user?.email} size="sm" className="ring-2 ring-accent/20" />
                  <span className="hidden lg:block text-[15px] font-semibold text-ink-2 max-w-[12rem] truncate">
                    {user?.full_name || user?.email}
                  </span>
                </div>
              </div>
            </header>

            <main className="flex-1 px-4 sm:px-6 lg:px-8 pb-24 md:pb-10 pt-6">
              <div className="max-w-6xl mx-auto w-full">{children}</div>
            </main>
          </div>

          {/* mobile bottom tab bar */}
          <nav className="fixed md:hidden bottom-0 inset-x-0 z-40 bg-surface border-t border-line/50 pb-[env(safe-area-inset-bottom)] shadow-lg backdrop-blur-md">
            <div className="flex h-14">
              {tabItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex-1 flex flex-col items-center justify-center gap-1 text-[10px] transition-colors duration-150 relative",
                      active ? "text-accent-text font-bold" : "text-ink-3 font-medium"
                    )}
                  >
                    <Icon className="w-5.5 h-5.5" strokeWidth={active ? 2.2 : 2} />
                    {item.short}
                    {active && <span className="absolute top-0 h-[3px] w-8 rounded-pill bg-accent" />}
                  </Link>
                );
              })}
              <button
                onClick={() => setSidebarOpen(true)}
                className="flex-1 flex flex-col items-center justify-center gap-1 text-[10px] text-ink-3 font-medium"
              >
                <MoreHorizontal className="w-5.5 h-5.5" />
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