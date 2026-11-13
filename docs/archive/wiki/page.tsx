import Link from "next/link";
import { BookOpen, Wifi, Server, Radio, Network } from "lucide-react";

export const metadata = {
  title: "Wiki Technique — Guides Opérationnels",
  description: "Documentation technique et guides opérationnels pour l'infrastructure réseau et systèmes",
  robots: { index: false, follow: false },
};

const tps = [
  {
    slug: "lorawan",
    icon: Radio,
    color: "from-emerald-500 to-teal-600",
    badge: "bg-emerald-100 text-emerald-700",
    title: "LoRaWAN & ChirpStack",
    subtitle: "Modules 0 à 4",
    description:
      "Déploiement de capteurs LoRaWAN avec ChirpStack, MQTT et Node-RED sur Raspberry Pi. Installation, enregistrement passerelle, intégration MQTT, sécurisation TLS et infrastructure multi-projets.",
    tps: ["Module 0 — Installation ChirpStack", "Module 1 — Passerelle & premier capteur", "Module 2 — MQTT & Node-RED", "Module 3 — Sécurisation TLS", "Module 4 — Infrastructure multi-projets"],
    duration: "8h total",
  },
  {
    slug: "voip",
    icon: Wifi,
    color: "from-blue-500 to-indigo-600",
    badge: "bg-blue-100 text-blue-700",
    title: "VoIP — Asterisk PJSIP",
    subtitle: "Modules 1 à 4",
    description:
      "Configuration et sécurisation PJSIP avec Asterisk, déploiement Docker, supervision Zabbix/Grafana et optimisation QoS mobile.",
    tps: ["Module 1 — Analyse & Sécurisation PJSIP", "Module 2 — Docker PJSIP", "Module 3 — Supervision Zabbix/Grafana", "Module 4 — QoS Mobile PJSIP"],
    duration: "8h total",
  },
  {
    slug: "windows-server-2022",
    icon: Server,
    color: "from-violet-500 to-purple-600",
    badge: "bg-violet-100 text-violet-700",
    title: "Windows Server 2022 GUI",
    subtitle: "Modules 1 à 4",
    description:
      "Infrastructure Active Directory, DNS, DHCP, VPN RADIUS, DNSSEC, Wi-Fi WPA2-Enterprise, 802.1X, GPO et haute disponibilité — 100% interface graphique, sans ligne de commande.",
    tps: ["Module 1 — AD DS, DNS, DHCP, VPN", "Module 2 — DNSSEC & Wi-Fi WPA2-Ent.", "Module 3 — 802.1X Filaire & GPO", "Module 4 — Haute Disponibilité AD/DHCP"],
    duration: "16h total",
  },
  {
    slug: "cisco",
    icon: Network,
    color: "from-orange-500 to-red-600",
    badge: "bg-orange-100 text-orange-700",
    title: "Réseaux Cisco",
    subtitle: "Modules 1 et 2",
    description:
      "Configuration réseau multi-switches avec VLANs, STP Rapid PVST+, sécurisation couche 2, supervision SNMP, EtherChannel LACP et ACLs.",
    tps: ["Module 1 — VLANs, STP & SNMP", "Module 2 — EtherChannel & ACLs"],
    duration: "4h total",
  },
];

export default function WikiPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-10">
          <div className="flex items-center gap-3 mb-3">
            <BookOpen className="w-8 h-8 text-indigo-600" />
            <span className="text-xs font-semibold uppercase tracking-widest text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full">
              Wiki interne
            </span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Wiki Technique — Guides Opérationnels
          </h1>
          <p className="text-gray-500 text-base max-w-2xl">
            Base documentaire interne pour le déploiement, la configuration et l'exploitation des environnements réseau.
            Chaque section regroupe les procédures, configurations et bonnes pratiques.
          </p>
        </div>
      </div>

      {/* Cards grid */}
      <div className="max-w-5xl mx-auto px-6 py-10 grid grid-cols-1 md:grid-cols-2 gap-6">
        {tps.map((tp) => {
          const Icon = tp.icon;
          return (
            <Link
              key={tp.slug}
              href={`/wiki/${tp.slug}`}
              className="group bg-white rounded-2xl border border-gray-200 hover:border-gray-300 hover:shadow-lg transition-all duration-200 overflow-hidden"
            >
              <div className={`h-2 w-full bg-gradient-to-r ${tp.color}`} />
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-2.5 rounded-xl bg-gradient-to-br ${tp.color} text-white`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex gap-2">
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${tp.badge}`}>
                      {tp.subtitle}
                    </span>
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                      {tp.duration}
                    </span>
                  </div>
                </div>
                <h2 className="text-lg font-bold text-gray-900 mb-2 group-hover:text-indigo-600 transition-colors">
                  {tp.title}
                </h2>
                <p className="text-sm text-gray-500 mb-4 leading-relaxed">{tp.description}</p>
                <ul className="space-y-1">
                  {tp.tps.map((item, i) => (
                    <li key={i} className="text-xs text-gray-600 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-300 flex-shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </Link>
          );
        })}
      </div>

      <footer className="max-w-5xl mx-auto px-6 pb-10 text-center text-xs text-gray-400">
        Usage interne — radarapp.fr/wiki
      </footer>
    </div>
  );
}
