"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { Loader2 } from "lucide-react";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Read directly from the synchronous Zustand state to bypass React's render cycle lag
    const state = useAuthStore.getState();

    if (!state.isAuthenticated) {
      const currentPath = window.location.pathname;
      router.replace(`/auth/login?next=${encodeURIComponent(currentPath)}`);
      return;
    }

    if (allowedRoles && state.user && !allowedRoles.includes(state.user.role)) {
      if (state.user.role === 'admin') router.replace("/admin");
      else if (state.user.role === 'citizen') router.replace("/citizen");
      else router.replace("/workbench");
      return;
    }

    setIsChecking(false);
  }, [isAuthenticated, user, allowedRoles, router]);

  // Show loading while checking
  if (isChecking || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <Loader2 className="w-6 h-6 animate-spin text-ink-3" />
      </div>
    );
  }

  // Role check
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}
