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
  Menu,
  Bell,
  Search,
  ShieldAlert,
  Users,
  CheckSquare,
  ArrowLeft,
  Network,
  LayoutDashboard,
  ShieldCheck,
  Home,
  AlertTriangle,
  Building,
  Siren,
  UserCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuthStore } from "@/lib/auth-store";
import { ThemeToggle } from "@/components/theme-toggle";

const workbenchNavigation = [
  { name: 'Dashboard', href: '/workbench', icon: Activity },
  { name: 'Report Scam', href: '/report', icon: ShieldAlert },
  { name: 'Spatial Map', href: '/workbench/map', icon: Map },
  { name: 'Graph Explorer', href: '/workbench/graph', icon: Network },
  { name: 'Reports (FIR/TPR)', href: '/workbench/reports', icon: FileText },
  { name: 'Prevention Suite', href: '/prevention', icon: ShieldCheck },
  { name: 'AI Co-Pilot', href: '/copilot', icon: Bell },
];

const adminSections = [
  {
    label: 'Admin Console',
    color: 'purple',
    items: [
      { name: 'Admin Dashboard', href: '/admin', icon: Activity },
      { name: 'User Management', href: '/admin/users', icon: Users },
      { name: 'Pending Approvals', href: '/admin/approvals', icon: CheckSquare },
      { name: 'National Analytics', href: '/admin/intelligence', icon: Network },
      { name: 'Platform Settings', href: '/admin/settings', icon: Settings },
    ]
  },
  {
    label: 'Investigator / Police',
    color: 'blue',
    items: [
      { name: 'Investigator Workbench', href: '/workbench', icon: Siren },
      { name: 'Reports (FIR/TPR)', href: '/workbench/reports', icon: FileText },
      { name: 'Spatial Map', href: '/workbench/map', icon: Map },
      { name: 'Graph Explorer', href: '/workbench/graph', icon: Network },
      { name: 'AI Co-Pilot', href: '/copilot', icon: Bell },
    ]
  },
  {
    label: 'Banker / Nodal Officer',
    color: 'green',
    items: [
      { name: 'Nodal Dashboard', href: '/banker', icon: Building },
      { name: 'Report Scam', href: '/report', icon: ShieldAlert },
      { name: 'Prevention Suite', href: '/prevention', icon: ShieldCheck },
      { name: 'Spatial Map', href: '/workbench/map', icon: Map },
    ]
  },
  {
    label: 'Citizen',
    color: 'amber',
    items: [
      { name: 'Citizen Dashboard', href: '/citizen', icon: UserCircle },
      { name: 'Report Scam', href: '/report', icon: ShieldAlert },
      { name: 'Prevention Suite', href: '/prevention', icon: ShieldCheck },
      { name: 'Spatial Map', href: '/workbench/map', icon: Map },
    ]
  },
];

const adminNavigation = adminSections.flatMap(s => s.items);
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { logout, user } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/auth/login");
  };

  // Determine what part of the app we are in
  const isAdminSection = pathname.startsWith("/admin");
  const isCitizenSection = pathname.startsWith("/citizen");
  const isWorkbenchMap = pathname === "/workbench/map";
  const isWorkbenchSection = pathname.startsWith("/workbench") && !isWorkbenchMap;

  // Determine allowed roles for this section based on path
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

  // Populate Sidebar Navigation strictly based on the User's Role
  let navigation: any[] = [];
  if (user?.role === 'admin') {
    navigation = adminNavigation; // Will render all sections
  } else if (user?.role === 'police' || user?.role === 'cyber_cell') {
    navigation = adminSections.find(s => s.label === 'Investigator / Police')?.items || [];
  } else if (user?.role === 'banker' || user?.role === 'bank_employee') {
    navigation = adminSections.find(s => s.label === 'Banker / Nodal Officer')?.items || [];
  } else if (user?.role === 'citizen') {
    navigation = adminSections.find(s => s.label === 'Citizen')?.items || [];
  }

  return (
    <ProtectedRoute allowedRoles={allowedRoles}>
      <div className="min-h-screen bg-muted/30 flex">
        {/* Sidebar */}
        <aside className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 flex flex-col",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          {isAdminSection ? (
            <div className="h-16 flex items-center gap-2 px-6 border-b border-border bg-purple-500/5">
              <Settings className="w-8 h-8 text-purple-500" />
              <span className="text-xl font-bold">Admin Console</span>
            </div>
          ) : (
            <div className="h-16 flex items-center gap-2 px-6 border-b border-border">
              <Shield className="w-8 h-8 text-primary" />
              <span className="text-xl font-bold">Rakshak Core</span>
            </div>
          )}
          
          <div className="p-4 space-y-1 flex-1 overflow-y-auto">
            {user?.role === 'admin' ? (
              <>
                {adminSections.map((section, sIdx) => {
                  const colorMap: Record<string, { dot: string, activeText: string, activeBg: string }> = {
                    purple: { dot: 'bg-purple-500', activeText: 'text-purple-600 dark:text-purple-400', activeBg: 'bg-purple-500/10' },
                    blue:   { dot: 'bg-blue-500',   activeText: 'text-blue-600 dark:text-blue-400',     activeBg: 'bg-blue-500/10' },
                    green:  { dot: 'bg-green-500',  activeText: 'text-green-600 dark:text-green-400',   activeBg: 'bg-green-500/10' },
                    amber:  { dot: 'bg-amber-500',  activeText: 'text-amber-600 dark:text-amber-400',   activeBg: 'bg-amber-500/10' },
                  };
                  const colors = colorMap[section.color] || colorMap.purple;

                  return (
                    <div key={section.label} className={sIdx > 0 ? 'pt-4 mt-4 border-t border-border' : ''}>
                      <div className="flex items-center gap-2 px-3 mb-2">
                        <span className={cn("w-2 h-2 rounded-full", colors.dot)} />
                        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{section.label}</span>
                      </div>
                      {section.items.map((item) => {
                        const isActive = pathname === item.href;
                        const Icon = item.icon;
                        return (
                          <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                              "flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors",
                              isActive 
                                ? `${colors.activeBg} ${colors.activeText}`
                                : "text-muted-foreground hover:bg-muted hover:text-foreground"
                            )}
                          >
                            <Icon className={cn("w-5 h-5", isActive ? colors.activeText : "text-muted-foreground")} />
                            {item.name}
                          </Link>
                        );
                      })}
                    </div>
                  );
                })}
              </>
            ) : (
              <>
                {navigation.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
                        isActive 
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      )}
                    >
                      <Icon className={cn("w-5 h-5", isActive ? "text-primary" : "text-muted-foreground")} />
                      {item.name}
                    </Link>
                  );
                })}
              </>
            )}
          </div>

          <div className="p-4 border-t border-border mt-auto">
            <button 
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-16 bg-card border-b border-border flex items-center justify-between px-4 sm:px-6 sticky top-0 z-40">
            <button 
              className="md:hidden p-2 -ml-2 text-muted-foreground hover:text-foreground rounded-lg"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <Menu className="w-6 h-6" />
            </button>

            {!isAdminSection ? (
              <div className="flex-1 flex items-center gap-4 max-w-2xl ml-4 md:ml-0">
                <div className="relative w-full max-w-md hidden sm:block">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input 
                    type="text" 
                    placeholder="Search threats, IPs, or domains..." 
                    className="w-full pl-10 pr-4 py-2 bg-muted border-transparent rounded-full text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
                  />
                </div>
              </div>
            ) : (
              <div className="flex-1" />
            )}

            <div className="flex items-center gap-3">
              <ThemeToggle />
              <button className="relative p-2 text-muted-foreground hover:text-foreground rounded-full hover:bg-muted transition-colors">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-card" />
              </button>
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-purple-500 border-2 border-card shadow-sm cursor-pointer flex items-center justify-center text-xs font-bold text-white">
                {user?.email?.charAt(0).toUpperCase() || "U"}
              </div>
            </div>
          </header>

          <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
            <div className="max-w-7xl mx-auto space-y-6">
              {children}
            </div>
          </main>
        </div>

        {/* Mobile Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </div>
    </ProtectedRoute>
  );
}
