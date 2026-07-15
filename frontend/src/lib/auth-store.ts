import { create } from "zustand";

export type UserRole =
  | "admin"
  | "citizen"
  | "police"
  | "cyber_cell"
  | "banker"
  | "bank_employee";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  full_name?: string;
  station_phone_number?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isHydrated: boolean;

  login: (token: string, user: User) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isHydrated: false,

  login: (token, user) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("token", token);
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("dr_last_activity", Date.now().toString());
    }

    set({
      token,
      user,
      isAuthenticated: true,
      isHydrated: true,
    });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      localStorage.removeItem("dr_last_activity");
    }

    set({
      token: null,
      user: null,
      isAuthenticated: false,
      isHydrated: true,
    });
  },

  hydrate: () => {
    if (typeof window === "undefined") return;

    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");

    if (!token || !userStr) {
      set({
        token: null,
        user: null,
        isAuthenticated: false,
        isHydrated: true,
      });
      return;
    }

    try {
      const user = JSON.parse(userStr) as User;

      set({
        token,
        user,
        isAuthenticated: true,
        isHydrated: true,
      });
    } catch {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      localStorage.removeItem("dr_last_activity");

      set({
        token: null,
        user: null,
        isAuthenticated: false,
        isHydrated: true,
      });
    }
  },
}));