"use client";

import { useSubscriptionStore } from "./subscriptionStore";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "@/lib/types";
import { authApi, api } from "@/lib/api";

interface LoginResult {
  success: boolean;
  requires2FA?: boolean;
  tempToken?: string;
}
export interface PendingMFA {
  tempToken: string;
  methods: string[];
  destinations: Record<string, string>;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  rememberMe: boolean;
  lastLoginEmail: string | null;
  pending2FA: PendingMFA | null;
  setPending2FA: (value: PendingMFA) => void;
  complete2FA: (method: string, code: string, trustDevice?: boolean) => Promise<void>;
  
  // Actions
  login: (email: string, password: string, rememberMe?: boolean, totpCode?: string) => Promise<LoginResult>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  setUser: (user: User | null) => void;
  setRememberMe: (value: boolean) => void;
  setTokens: (accessToken: string, refreshToken: string) => Promise<void>;
  initializeAuth: () => Promise<void>;
  clearPending2FA: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      rememberMe: true,
      lastLoginEmail: null,
      pending2FA: null,

      login: async (email: string, password: string, rememberMe = true, totpCode?: string): Promise<LoginResult> => {
        set({ isLoading: true });
        try {
          const response = await authApi.login(email, password, totpCode);
          
          // Check if 2FA is required
          if (response.requires_2fa) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            set({ 
              isLoading: false,
              user: null, isAuthenticated: false,
              rememberMe, lastLoginEmail: rememberMe ? email : null,
              pending2FA: { tempToken: response.temp_token, methods: response.methods || [], destinations: response.destinations || {} }
            });
            return { success: false, requires2FA: true, tempToken: response.temp_token };
          }
          
          // Normal login success
          localStorage.setItem("access_token", response.access_token);
          localStorage.setItem("refresh_token", response.refresh_token);
          
          // Store remember me preference
          set({ rememberMe, lastLoginEmail: rememberMe ? email : null, pending2FA: null });
          
          // Fetch user after login
          await get().fetchUser();
          
          // Auto-select first workspace if none selected
          const currentWsId = localStorage.getItem("current_workspace_id");
          if (!currentWsId) {
            try {
              const wsResponse = await api.get("/workspaces");
              const workspaces = wsResponse.data.items;
              if (workspaces && workspaces.length > 0) {
                localStorage.setItem("current_workspace_id", workspaces[0].id.toString());
              }
            } catch (e) {
              // Ignore workspace fetch errors
            }
          }
          
          return { success: true };
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },
      
      clearPending2FA: () => {
        set({ pending2FA: null });
      },
      setPending2FA: value => set({ pending2FA: value, user: null, isAuthenticated: false, isLoading: false }),
      complete2FA: async (method, code, trustDevice = false) => {
        const pending = get().pending2FA;
        if (!pending) throw new Error('Vérification expirée. Reconnectez-vous.');
        const result = await authApi.mfaComplete(pending.tempToken, method, code, trustDevice);
        await get().setTokens(result.access_token, result.refresh_token);
        set({ pending2FA: null });
      },

      logout: () => {
        // Revoke with the captured credential before local storage is cleared.
        const token = localStorage.getItem("access_token");
        if (token) void fetch("/api/v1/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${token}` }, keepalive: true }).catch(() => undefined);
        useSubscriptionStore.getState().reset();
        localStorage.removeItem("radar-subscription");
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("current_workspace_id");
        set({ user: null, isAuthenticated: false, isLoading: false, pending2FA: null });
      },

      fetchUser: async () => {
        const token = localStorage.getItem("access_token");
        if (!token) {
          set({ user: null, isAuthenticated: false, isLoading: false });
          return;
        }

        try {
          const user = await authApi.getMe();
          set({ user, isAuthenticated: true, isLoading: false });
        } catch {
          // Try to refresh token before giving up
          const refreshToken = localStorage.getItem("refresh_token");
          if (refreshToken) {
            try {
              const response = await authApi.refresh(refreshToken);
              localStorage.setItem("access_token", response.access_token);
              if (response.refresh_token) {
                localStorage.setItem("refresh_token", response.refresh_token);
              }
              // Retry fetching user
              const user = await authApi.getMe();
              set({ user, isAuthenticated: true, isLoading: false });
              return;
            } catch {
              // Refresh failed
            }
          }
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          set({ user: null, isAuthenticated: false, isLoading: false });
        }
      },

      setUser: (user: User | null) => {
        set({ user, isAuthenticated: !!user });
      },
      
      setRememberMe: (value: boolean) => {
        set({ rememberMe: value });
      },
      
      setTokens: async (accessToken: string, refreshToken: string) => {
        // Store tokens (from SSO callback)
        localStorage.setItem("access_token", accessToken);
        localStorage.setItem("refresh_token", refreshToken);
        // Fetch user info
        await get().fetchUser();
        
        // Auto-select first workspace if none selected
        const currentWsId = localStorage.getItem("current_workspace_id");
        if (!currentWsId) {
          try {
            const wsResponse = await api.get("/workspaces");
            const workspaces = wsResponse.data.items;
            if (workspaces && workspaces.length > 0) {
              localStorage.setItem("current_workspace_id", workspaces[0].id.toString());
            }
          } catch (e) {
            // Ignore workspace fetch errors
          }
        }
      },

      initializeAuth: async () => {
        const token = localStorage.getItem("access_token");
        if (token) {
          await get().fetchUser();
        } else {
          set({ isLoading: false });
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated,
        rememberMe: state.rememberMe,
        lastLoginEmail: state.lastLoginEmail,
      }),
    }
  )
);
