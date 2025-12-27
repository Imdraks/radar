"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Target, Loader2 } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import api from "@/lib/api";

// SSO Icons
const GoogleIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24">
    <path
      fill="currentColor"
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
    />
    <path
      fill="currentColor"
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
    />
    <path
      fill="currentColor"
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
    />
    <path
      fill="currentColor"
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
    />
  </svg>
);

const AppleIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09l.01-.01zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
  </svg>
);

const loginSchema = z.object({
  email: z.string().email("Email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

type LoginForm = z.infer<typeof loginSchema>;

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, rememberMe, setRememberMe, lastLoginEmail, isAuthenticated, isLoading: authLoading } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [checkingSetup, setCheckingSetup] = useState(true);
  const [ssoLoading, setSsoLoading] = useState<string | null>(null);
  const [ssoProviders, setSsoProviders] = useState<{ id: string; name: string; enabled: boolean }[]>([]);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  // Auto-redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.push("/dashboard");
    }
  }, [authLoading, isAuthenticated, router]);

  // Pre-fill email if remembered
  useEffect(() => {
    if (lastLoginEmail && rememberMe) {
      setValue("email", lastLoginEmail);
    }
  }, [lastLoginEmail, rememberMe, setValue]);

  // Check if setup is needed
  useEffect(() => {
    const checkSetup = async () => {
      try {
        const response = await api.get("/auth/setup-check");
        if (response.data.needs_setup) {
          router.push("/setup");
          return;
        }
        
        // Fetch available SSO providers
        try {
          const providersResponse = await api.get("/auth/sso/providers");
          setSsoProviders(providersResponse.data.providers || []);
        } catch {
          // SSO not configured
        }
      } catch (err) {
        // API not available, continue to login
      }
      setCheckingSetup(false);
    };
    checkSetup();
  }, [router]);
  
  // Check for SSO error in URL
  useEffect(() => {
    const ssoError = searchParams.get("error");
    if (ssoError) {
      setError(`Erreur SSO: ${ssoError}`);
    }
  }, [searchParams]);
  
  // Handle SSO login
  const handleSsoLogin = async (provider: string) => {
    setSsoLoading(provider);
    setError(null);
    
    try {
      const response = await api.get(`/auth/sso/${provider}/init`);
      // Redirect to OAuth provider
      window.location.href = response.data.auth_url;
    } catch (err) {
      setError(`Erreur lors de l'initialisation de ${provider}`);
      setSsoLoading(null);
    }
  };

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    setIsLoading(true);

    try {
      await login(data.email, data.password, rememberMe);
      router.push("/dashboard");
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string | object } } };
      const detail = error?.response?.data?.detail;
      // Handle both string and object error formats
      if (typeof detail === "string") {
        setError(detail);
      } else if (detail && typeof detail === "object") {
        // Pydantic validation error format
        setError("Erreur de validation. Vérifiez vos identifiants.");
      } else {
        setError("Identifiants invalides");
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (checkingSetup || (!authLoading && isAuthenticated)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-gray-900 dark:to-gray-950">
        <div className="flex flex-col items-center gap-4 animate-pulse">
          <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
          <p className="text-muted-foreground text-sm">Chargement...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 via-background to-primary/10 dark:from-gray-900 dark:via-gray-950 dark:to-primary/5 p-4 safe-top safe-bottom">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/10 rounded-full blur-3xl animate-pulse-soft" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-primary/5 rounded-full blur-3xl animate-pulse-soft animate-delay-500" />
      </div>
      
      <Card className="w-full max-w-md relative animate-fade-in-up shadow-xl border-0 dark:border dark:border-gray-800">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-lg shadow-primary/30 animate-bounce-soft">
              <Target className="h-8 w-8 text-primary-foreground" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400 bg-clip-text text-transparent">
            Radar
          </CardTitle>
          <CardDescription className="text-muted-foreground">
            Connectez-vous pour accéder à la plateforme
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* SSO Buttons - Always show */}
          <div className="space-y-3">
            {/* Google SSO */}
            <Button
              variant="outline"
              className="w-full h-12 text-base font-medium hover-lift transition-all duration-200 hover:border-primary/50 hover:bg-primary/5"
              onClick={() => handleSsoLogin("google")}
              disabled={ssoLoading !== null}
            >
              {ssoLoading === "google" ? (
                <Loader2 className="mr-3 h-5 w-5 animate-spin" />
              ) : (
                <GoogleIcon className="mr-3 h-5 w-5" />
              )}
              Continuer avec Google
            </Button>
            
            {/* Apple SSO - Coming Soon */}
            <Button
              variant="outline"
              className="w-full h-12 text-base font-medium opacity-50 cursor-not-allowed"
              disabled={true}
            >
              <AppleIcon className="mr-3 h-5 w-5" />
              Apple — Prochainement
            </Button>
          </div>
            
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-3 text-muted-foreground">
                Ou avec email
              </span>
            </div>
          </div>
          
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {error && (
              <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-sm animate-fade-in flex items-center gap-2">
                <svg className="h-4 w-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="vous@example.com"
                className="h-12 text-base"
                {...register("email")}
                disabled={isLoading}
              />
              {errors.email && (
                <p className="text-sm text-destructive animate-fade-in">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                className="h-12 text-base"
                {...register("password")}
                disabled={isLoading}
              />
              {errors.password && (
                <p className="text-sm text-destructive animate-fade-in">{errors.password.message}</p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="rememberMe"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked === true)}
              />
              <Label htmlFor="rememberMe" className="text-sm font-normal cursor-pointer">
                Se souvenir de moi
              </Label>
            </div>

            <Button 
              type="submit" 
              className="w-full h-12 text-base font-semibold hover-glow transition-all duration-200" 
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Connexion...
                </>
              ) : (
                "Se connecter"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-gray-900 dark:to-gray-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center animate-pulse">
            <Target className="h-8 w-8 text-primary" />
          </div>
        </div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
