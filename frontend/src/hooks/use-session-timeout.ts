"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";

const TIMEOUT_DURATION = 30 * 60 * 1000; // 30 minutes in milliseconds
const LOCAL_STORAGE_KEY = "dr_last_activity";

export function useSessionTimeout() {
  const { isAuthenticated, logout } = useAuthStore();
  const router = useRouter();
  const logoutRef = useRef(logout);
  const routerRef = useRef(router);

  // Sync refs to avoid dependency updates in useEffect
  useEffect(() => {
    logoutRef.current = logout;
    routerRef.current = router;
  }, [logout, router]);

  useEffect(() => {
    if (!isAuthenticated) return;

    // Helper to log out and redirect
    const performLogout = () => {
      logoutRef.current();
      routerRef.current.push("/auth/login");
    };

    // Check if the session has timed out
    const checkTimeout = () => {
      const lastActivity = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (!lastActivity) {
        // If no activity recorded yet, set it now
        localStorage.setItem(LOCAL_STORAGE_KEY, Date.now().toString());
        return;
      }

      const elapsed = Date.now() - parseInt(lastActivity, 10);
      if (elapsed > TIMEOUT_DURATION) {
        performLogout();
      }
    };

    // Update the last activity timestamp (throttled to avoid heavy writes)
    let lastWriteTime = 0;
    const updateActivity = () => {
      const now = Date.now();
      if (now - lastWriteTime > 5000) { // update every 5 seconds maximum
        localStorage.setItem(LOCAL_STORAGE_KEY, now.toString());
        lastWriteTime = now;
      }
    };

    // Run initial check
    checkTimeout();

    // Register user activity events to keep the session alive
    const events = ["mousemove", "mousedown", "keydown", "scroll", "touchstart"];
    events.forEach((event) => {
      window.addEventListener(event, updateActivity);
    });

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        checkTimeout();
      }
    };

    // Cross-tab synchronization
    const handleStorageChange = (e: StorageEvent) => {
      // If token is removed in another tab, sync the logout here
      if (e.key === "token" && !e.newValue) {
        performLogout();
      }
      // If another tab updates activity, we can sync it (implicitly handled by checking localStorage later)
    };

    window.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("storage", handleStorageChange);
    const interval = setInterval(checkTimeout, 10000); // Check every 10 seconds

    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, updateActivity);
      });
      window.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("storage", handleStorageChange);
      clearInterval(interval);
    };
  }, [isAuthenticated]);
}
