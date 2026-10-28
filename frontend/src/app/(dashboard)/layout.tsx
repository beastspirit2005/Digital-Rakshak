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
  Eye,
  CreditCard,
  Building2,
  Sparkles,
  MapPin,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

import { useAuthStore } from "@/lib/auth-store";
import { ThemeToggle } from "@/components/theme-toggle";
import dynamic from "next/dynamic";

const GlobalChatWidget = dynamic(
  () => import("@/components/global-chat-widget").then((mod) => mod.GlobalChatWidget),
  { ssr: false }
);
import { ToastProvider } from "@/components/ui/toast";
import { Avatar } from "@/components/ui/avatar";
import { useSessionTimeout } from "@/hooks/use-session-timeout";
import { NotificationBell } from "@/components/notifications/notification-bell";

export interface NavItem {
  name: string;
  short: string;
  href: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

export const adminNavSections: NavSection[] = [
  {
    label: "Tactical Operations",
    items: [
      { name: "Command center", short: "Command", href: "/admin/command-center", icon: Siren },
      { name: "Nationwide surveillance", short: "Surveillance", href: "/admin/victims-map", icon: MapPin },
      { name: "Universal case tracker", short: "Tracker", href: "/admin/tracker", icon: Activity },
      { name: "Incident register", short: "Incidents", href: "/admin/reports", icon: FileText },
      { name: "Official KYC approvals", short: "Approvals", href: "/admin/approvals", icon: CheckSquare },
    ],
  },
  {
    label: "Intelligence & Governance",
    items: [
      { name: "National analytics", short: "Analytics", href: "/admin/intelligence", icon: Network },
      { name: "Misconduct & disputes", short: "Disputes", href: "/admin/disputes", icon: ShieldAlert },
      { name: "AI pipeline health", short: "AI Health", href: "/admin/ai-health", icon: Bot },
    ],
  },
  {
    label: "Platform Management",
    items: [
      { name: "User directory", short: "Users", href: "/admin/users", icon: Users },
      { name: "Enterprise B2B portal", short: "B2B API", href: "/business", icon: Building2 },
      { name: "Platform settings", short: "Settings", href: "/admin/settings", icon: Settings },
      { name: "Support desk", short: "Support", href: "/admin/support", icon: LifeBuoy },
      { name: "My account", short: "Account", href: "/account", icon: UserCircle },
    ],
  },
];

export const investigatorNavSections: NavSection[] = [
  {
    label: "Patrol & Tactical Dispatch",
    items: [
      { name: "Investigation workbench", short: "Workbench", href: "/workbench", icon: Siren },
      { name: "Victims proximity radar", short: "Proximity", href: "/police/victims-map", icon: MapPin },
      { name: "Case register & dockets", short: "Cases", href: "/workbench/reports", icon: FileText },
    ],
  },
  {
    label: "Forensics & Intelligence",
    items: [
      { name: "Spatial crime map", short: "Spatial", href: "/workbench/map", icon: Map },
      { name: "Suspect graph explorer", short: "Graph", href: "/workbench/graph", icon: Network },
      { name: "Counterfeit & APK hub", short: "Counterfeit", href: "/workbench/counterfeit", icon: Eye },
      { name: "AI investigation co-pilot", short: "Co-pilot", href: "/copilot", icon: Bot },
    ],
  },
  {
    label: "Duty Station Desk",
    items: [
      { name: "My account & duty station", short: "Duty Station", href: "/account", icon: UserCircle },
      { name: "Investigator SOPs & guide", short: "SOPs", href: "/help", icon: LifeBuoy },
    ],
  },
];

export const nodalNavSections: NavSection[] = [
  {
    label: "Fraud Interception & Liens",
    items: [
      { name: "Nodal operations desk", short: "Desk", href: "/banker", icon: Building },
      { name: "Live transaction stream", short: "Stream", href: "/banker/transactions", icon: CreditCard },
    ],
  },
  {
    label: "Institutional Operations",
    items: [
      { name: "Core banking B2B API", short: "B2B API", href: "/business", icon: Building2 },
    ],
  },
  {
    label: "Branch Desk & Compliance",
    items: [
      { name: "My account & branch desk", short: "Branch Desk", href: "/account", icon: UserCircle },
      { name: "RBI compliance manual", short: "Compliance", href: "/help", icon: LifeBuoy },
    ],
  },
];

export const citizenNavSections: NavSection[] = [
  {
    label: "Protection & Incidents",
    items: [
      { name: "My cyber reports", short: "Reports", href: "/citizen", icon: FileText },
      { name: "Report cyber fraud", short: "Report", href: "/report", icon: ShieldAlert },
      { name: "Personal Pro shield", short: "Pro Shield", href: "/personal", icon: Sparkles },
    ],
  },
  {
    label: "Awareness & Privacy",
    items: [
      { name: "Scam prevention hub", short: "Prevention", href: "/prevention", icon: ShieldCheck },
      { name: "My account & privacy", short: "Account", href: "/account", icon: UserCircle },
      { name: "Cyber safety helpdesk", short: "Helpdesk", href: "/help", icon: LifeBuoy },
    ],
  },
];

type PersonaType = "admin" | "investigator" | "nodal" | "citizen";

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
  const [personaOverride, setPersonaOverride] = useState<PersonaType | null>(null);
  const { logout, user } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/auth/login");
  };

  const activePersona: PersonaType = useMemo(() => {
    if (user?.role !== "admin") {
      if (user?.role === "police" || user?.role === "cyber_cell") return "investigator";
      if (user?.role === "banker" || user?.role === "bank_employee") return "nodal";
      return "citizen";
    }

    if (personaOverride) return personaOverride;

    if (pathname.startsWith("/workbench") || pathname.startsWith("/police") || pathname.startsWith("/copilot")) {
      return "investigator";
    }
    if (pathname.startsWith("/banker")) {
      return "nodal";
    }
    if (pathname.startsWith("/citizen") || pathname.startsWith("/personal")) {
      return "citizen";
    }
    return "admin";
  }, [user?.role, personaOverride, pathname]);

  const handlePersonaChange = (newPersona: PersonaType) => {
    setPersonaOverride(newPersona);
    if (newPersona === "admin" && !pathname.startsWith("/admin")) {
      router.push("/admin/command-center");
    } else if (newPersona === "investigator" && !pathname.startsWith("/workbench") && !pathname.startsWith("/police") && !pathname.startsWith("/copilot")) {
      router.push("/workbench");
    } else if (newPersona === "nodal" && !pathname.startsWith("/banker")) {
      router.push("/banker");
    } else if (newPersona === "citizen" && !pathname.startsWith("/citizen") && !pathname.startsWith("/personal")) {
      router.push("/citizen");
    }
  };

  const roleMetadata = useMemo(() => {
    switch (activePersona) {
      case "admin":
        return {
          subtitle: "National Cyber Command",
          badge: "HQ Command",
          badgeClass: "bg-rose-500/10 text-rose-400 border border-rose-500/25",
        };
      case "investigator":
        return {
          subtitle: "LEA Threat Command",
          badge: "Law Enforcement",
          badgeClass: "bg-indigo-500/10 text-indigo-400 border border-indigo-500/25",
        };
      case "nodal":
        return {
          subtitle: "Financial Cyber Defense",
          badge: "Nodal Desk",
          badgeClass: "bg-amber-500/10 text-amber-400 border border-amber-500/25",
        };
      case "citizen":
      default:
        return {
          subtitle: "Citizen Cyber Protection",
          badge: "Citizen Shield",
          badgeClass: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25",
        };
    }
  }, [activePersona]);

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
  } else if (
    pathname.startsWith("/citizen") ||
    pathname.startsWith("/personal")
  ) {
    allowedRoles = ["admin", "citizen"];
  } else if (
    pathname.startsWith("/business")
  ) {
    allowedRoles = ["admin", "banker", "bank_employee"];
  } else if (
    pathname.startsWith("/account") ||
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
    switch (activePersona) {
      case "investigator":
        return investigatorNavSections;
      case "nodal":
        return nodalNavSections;
      case "citizen":
        return citizenNavSections;
      case "admin":
      default:
        return adminNavSections;
    }
  }, [activePersona]);

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
        <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-line flex items-center justify-center shrink-0">
          <BrandLogo size={28} />
        </div>

        <div className="min-w-0">
          <h1 className="font-display font-bold text-lg text-ink tracking-tight whitespace-nowrap">
            Digital Rakshak
          </h1>

          <p className="text-[9px] text-accent-text tracking-[0.22em] uppercase mt-1 whitespace-nowrap">
            {roleMetadata.subtitle}
          </p>
        </div>
      </Link>

      {/* Admin Persona Switcher for Quick Inspection & Jump */}
      {user?.role === "admin" && (
        <div className="px-3.5 pt-3.5 pb-2 border-b border-line/10">
          <div className="p-2.5 rounded-xl bg-surface-3/30 border border-line/30 space-y-1.5">
            <div className="flex items-center justify-between px-0.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-accent-text flex items-center gap-1">
                <Eye className="w-3 h-3 text-accent" /> Persona View
              </span>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-300 font-semibold border border-rose-500/25">
                ADMIN HQ
              </span>
            </div>
            <div className="relative">
              <select
                value={activePersona}
                onChange={(e) => handlePersonaChange(e.target.value as PersonaType)}
                className="w-full appearance-none text-xs font-semibold bg-surface border border-line rounded-lg px-2.5 py-2 pr-7 text-ink focus:outline-none focus:border-accent cursor-pointer shadow-sm"
              >
                <option value="admin" className="bg-surface text-ink">Command (Admin)</option>
                <option value="investigator" className="bg-surface text-ink">Threat Command (Police)</option>
                <option value="nodal" className="bg-surface text-ink">Financial Defense (Nodal)</option>
                <option value="citizen" className="bg-surface text-ink">Citizen Protection (User)</option>
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-ink-3 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        </div>
      )}

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
          <aside className="hidden md:flex w-60 shrink-0 flex-col bg-surface-2 sticky top-0 h-screen border-r border-line shadow-xl">
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
            <header className="h-20 flex items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 border-b border-line bg-bg/80 backdrop-blur-md sticky top-0 z-30">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setSidebarOpen(true)}
                  aria-label="Open navigation menu"
                  className="md:hidden p-2 rounded-control text-ink-2 hover:text-ink hover:bg-surface-2 transition-colors"
                >
                  <MoreHorizontal className="w-5 h-5" />
                </button>

                <div className="flex items-center gap-2">
                  <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase", roleMetadata.badgeClass)}>
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                    {roleMetadata.badge}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="hidden md:block relative w-full max-w-sm">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-ink-3" />
                  <input
                    type="search"
                    placeholder="Search cases, phone numbers, UPI IDs, domains..."
                    className="w-full h-11 pl-11 pr-12 bg-surface-2/60 hover:bg-surface-2 rounded-control text-[15px] text-ink placeholder:text-ink-3 border border-line hover:border-line-focus focus:border-accent focus:bg-surface focus:outline-none transition-all"
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-line/40 text-ink-3 pointer-events-none">
                    ⌘K
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <ThemeToggle />
                  <NotificationBell />
                  <Link
                    href="/account"
                    className="flex items-center gap-3 pl-2.5 border-l border-line hover:opacity-85 transition-opacity group"
                    title="My Account & Profile Settings"
                  >
                    <Avatar name={user?.full_name || user?.email} size="sm" className="ring-2 ring-accent/20 group-hover:ring-accent" />
                    <span className="hidden lg:block text-[15px] font-semibold text-ink-2 group-hover:text-ink max-w-[12rem] truncate transition-colors">
                      {user?.full_name || user?.email}
                    </span>
                  </Link>
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