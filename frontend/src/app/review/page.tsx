"use client";
import { useEffect, useState } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { clientError } from "@/lib/platform-clients";
import { activityTime } from "@/lib/activity";
type Review = {
  name: string;
  link: string;
  status: string;
  expires_at: string;
};
export default function ReviewPage() {
  const [token, setToken] = useState(""),
    [review, setReview] = useState<Review | null>(null),
    [error, setError] = useState(""),
    [name, setName] = useState(""),
    [feedback, setFeedback] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    const t = new URLSearchParams(location.hash.slice(1)).get("token") || "";
    setToken(t);
    history.replaceState(null, "", location.pathname);
    if (!t) {
      setError(
        "Ce lien est incomplet. Demandez un nouveau lien à votre interlocuteur.",
      );
      return;
    }
    axios
      .post(
        (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1/review/resolve",
        { token: t },
      )
      .then((r) => setReview(r.data))
      .catch((e) => setError(clientError(e)));
  }, []);
  async function decide(decision: string) {
    setBusy(true);
    setError("");
    try {
      const r = await axios.post(
        (process.env.NEXT_PUBLIC_API_URL ?? "") + "/api/v1/review/decide",
        { token, name, feedback, decision },
      );
      setReview((v) => (v ? { ...v, status: r.data.status } : null));
    } catch (e) {
      setError(clientError(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="min-h-screen bg-background px-4 py-12 text-foreground">
      <div className="mx-auto max-w-xl space-y-7">
        <p className="text-3xl font-semibold">
          Radar<span className="text-primary">.</span>
        </p>
        <header>
          <p className="radar-eyebrow">Validation d’un livrable</p>
          <h1 className="mt-3 break-words text-3xl font-semibold">
            {review?.name || "Votre avis fait avancer le projet."}
          </h1>
        </header>
        {error && (
          <p
            role="alert"
            className="rounded-xl border border-destructive/30 p-4 text-sm"
          >
            {error}
          </p>
        )}
        {review && (
          <section className="space-y-5 rounded-2xl border bg-card p-6">
            <p className="text-sm text-muted-foreground">
              Lien confidentiel valable jusqu’au{" "}
              {activityTime(review.expires_at)}. Toute personne possédant ce
              lien peut répondre. L’identité saisie est déclarative ; cette
              validation n’est pas une signature électronique.
            </p>
            <a
              href={review.link}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-block rounded-full bg-primary px-5 py-3 text-sm font-medium text-primary-foreground"
            >
              Consulter le livrable
            </a>
            {review.status === "pending" ? (
              <form
                className="space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  void decide("approved");
                }}
              >
                <Label htmlFor="review-name">Votre nom</Label>
                <Input
                  id="review-name"
                  minLength={2}
                  maxLength={200}
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <Label htmlFor="review-feedback">Votre retour</Label>
                <Textarea
                  id="review-feedback"
                  maxLength={4000}
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                />
                <div className="flex flex-wrap gap-3">
                  <Button disabled={busy}>Valider ce livrable</Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={
                      busy || name.trim().length < 2 || !feedback.trim()
                    }
                    onClick={() => decide("changes")}
                  >
                    Demander des modifications
                  </Button>
                </div>
              </form>
            ) : (
              <p role="status" className="font-medium">
                {review.status === "approved"
                  ? "Votre validation a été enregistrée."
                  : "Votre demande de modifications a été enregistrée."}
              </p>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
