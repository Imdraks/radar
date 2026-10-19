"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

export function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, fetchUser } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    fetchUser();
  }, [mounted, fetchUser]);

  useEffect(() => {
    if (!mounted) return;
    
    // Redirect to login if not authenticated
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [mounted, isLoading, isAuthenticated, router]);

  // Redirect based on role
  useEffect(() => {
    if (!mounted || isLoading || !isAuthenticated || !user) return;
    
    const isAdmin = user.is_superuser === true;

    // Non-admin trying to access admin-only pages → redirect to today
    const adminOnlyPages = ['/admin', '/workspaces', '/users'];
    const isAdminOnlyPage = adminOnlyPages.some(p => pathname === p || pathname.startsWith(p + '/'));
    if (!isAdmin && isAdminOnlyPage) {
      router.push("/today");
      return;
    }
    
  }, [mounted, isLoading, isAuthenticated, user, pathname, router]);

  // Check roles
  useEffect(() => {
    if (!mounted) return;
    
    if (!isLoading && isAuthenticated && user && requiredRoles?.length) {
      if (!requiredRoles.includes(user.role)) {
        router.push("/unauthorized");
      }
    }
  }, [mounted, isLoading, isAuthenticated, user, requiredRoles, router]);

  // Show loading until mounted and auth checked
  if (!mounted || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    );
  }

  // Require authentication
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}

export default ProtectedRoute;
