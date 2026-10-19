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

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  rememberMe: boolean;
  lastLoginEmail: string | null;
  pending2FA: { email: string; password: string; tempToken: string } | null;
  
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
            set({ 
              isLoading: false,
              pending2FA: { email, password, tempToken: response.temp_token }
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
              const workspaces = wsResponse.data;
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

      logout: () => {
        useSubscriptionStore.getState().reset();
        localStorage.removeItem("radar-subscription");
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("current_workspace_id");
        set({ user: null, isAuthenticated: false, isLoading: false });
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
            const workspaces = wsResponse.data;
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
