"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setTokens } = useAuthStore();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Connexion en cours...");
  const [isNewUser, setIsNewUser] = useState(false);
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const processCallback = async () => {
      const fragment = new URLSearchParams(window.location.hash.slice(1));
      const accessToken = fragment.get("access_token") || searchParams.get("access_token");
      const refreshToken = fragment.get("refresh_token") || searchParams.get("refresh_token");
      const isNew = (fragment.get("is_new") || searchParams.get("is_new")) === "true";
      window.history.replaceState(null, "", window.location.pathname);
      const error = searchParams.get("error");

      if (error) {
        setStatus("error");
        setMessage(`Erreur d'authentification: ${error}`);
        return;
      }

      if (!accessToken || !refreshToken) {
        setStatus("error");
        setMessage("Tokens manquants dans la réponse");
        return;
      }

      try {
        // Store tokens in auth store
        await setTokens(accessToken, refreshToken);
        setIsNewUser(isNew);
        setStatus("success");
        setMessage(isNew ? "Compte créé avec succès !" : "Connexion réussie !");

        const redirectPath = useAuthStore.getState().user?.is_superuser ? '/admin' : '/today';

        // Redirect after a short delay
        setTimeout(() => {
          router.push(redirectPath);
        }, 1500);
      } catch (err) {
        setStatus("error");
        setMessage("Erreur lors de la sauvegarde de la session");
      }
    };

    processCallback();
  }, [searchParams, setTokens, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 to-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            {status === "loading" && (
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            )}
            {status === "success" && (
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            )}
            {status === "error" && (
              <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
                <AlertCircle className="h-8 w-8 text-red-600" />
              </div>
            )}
          </div>
          <CardTitle className="text-2xl">
            {status === "loading" && "Authentification"}
            {status === "success" && (isNewUser ? "Bienvenue !" : "Content de vous revoir !")}
            {status === "error" && "Erreur"}
          </CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent>
          {status === "error" && (
            <div className="flex flex-col gap-3">
              <Button onClick={() => router.push("/login")} className="w-full">
                Retour à la connexion
              </Button>
            </div>
          )}
          {status === "success" && (
            <p className="text-center text-sm text-muted-foreground">
              Redirection vers le dashboard...
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}
