import { LandingHeader, LandingFooter, ForceLightMode } from '@/components/landing';
import { RadarLanding } from '@/components/landing/RadarLanding';
export const metadata = {
 title: 'Radar — Le point de repère de votre agence',
 description: 'Organisation, intelligence artistique, événements et gestion commerciale : Radar réunit les outils du quotidien des agences de communication, de production et d’événementiel.',
 alternates: { canonical: '/' },
};
export default function HomePage() {
 return <ForceLightMode><div className="radar-public"><LandingHeader /><main><RadarLanding /></main><LandingFooter /></div></ForceLightMode>;
}
