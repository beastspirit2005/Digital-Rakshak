"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore, type UserRole } from "@/lib/auth-store";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

function routeForRole(role: UserRole) {
  if (role === "admin") return "/admin";
  if (role === "citizen") return "/citizen";

  if (role === "banker" || role === "bank_employee") {
    return "/banker";
  }

  if (role === "police" || role === "cyber_cell") {
    return "/workbench";
  }

  return "/auth/login";
}

export function ProtectedRoute({
  children,
  allowedRoles,
}: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();

  const {
    user,
    token,
    isAuthenticated,
    isHydrated,
    hydrate,
  } = useAuthStore();

  useEffect(() => {
    if (!isHydrated) {
      hydrate();
      return;
    }

    if (!isAuthenticated || !token || !user) {
      router.replace(
        `/auth/login?next=${encodeURIComponent(pathname)}`
      );
      return;
    }

    if (
      allowedRoles &&
      !allowedRoles.includes(user.role)
    ) {
      router.replace(routeForRole(user.role));
    }
  }, [
    isHydrated,
    isAuthenticated,
    token,
    user,
    allowedRoles,
    pathname,
    router,
    hydrate,
  ]);

  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <p className="text-sm text-ink-2">
          Verifying secure access…
        </p>
      </div>
    );
  }

  if (!isAuthenticated || !token || !user) {
    return null;
  }

  if (
    allowedRoles &&
    !allowedRoles.includes(user.role)
  ) {
    return null;
  }

  return <>{children}</>;
}