import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Présentez votre agence et votre besoin à l’équipe Radar, en quelques étapes. Un contact dédié aux professionnels.",
  alternates: {
    canonical: "/contact",
  },
  openGraph: {
    title: "Contactez-nous | Radar",
    description:
      "Une question, un projet ou un besoin sur mesure ? Présentez votre demande professionnelle à l’équipe Radar.",
    url: "/contact",
  },
};

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
