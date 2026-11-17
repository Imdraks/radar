import {
  WikiLayout, TpSection, Phase, Steps, CodeBlock, Tip, Warning, Checklist, InfoTable,
} from "../components";

export const metadata = {
  title: "Guide Réseaux Cisco — VLANs, STP, SNMP, EtherChannel & ACLs",
  robots: { index: false, follow: false },
};

export default function CiscoPage() {
  return (
    <WikiLayout
      title="Réseaux Cisco — Guide Opérationnel"
      subtitle="Modules 1 et 2 · VLANs, STP, SNMP, EtherChannel, ACLs"
      description="Configuration réseau multi-switches avec VLANs, STP Rapid PVST+, sécurisation couche 2, supervision SNMP, EtherChannel LACP et ACLs pour la sécurisation inter-VLAN. Guide complet incluant scenarios pratiques et exercices."
      color="from-orange-500 to-red-600"
    >

      {/* TP 1 */}
      <TpSection number="Module 1" title="Réseau segmenté et sécurisé avec supervision SNMP" duration="2h">
        <Tip>
          <strong>Contexte :</strong> Une PME souhaite moderniser son infrastructure réseau en la segmentant selon ses services (Informatique, RH, Comptabilité), sécuriser les accès internes et mettre en place une supervision SNMP.
        </Tip>

        <div className="bg-white border border-gray-100 rounded-xl p-4">
          <h3 className="font-semibold text-gray-800 mb-3">Matériel et ressources</h3>
          <ul className="space-y-1.5 text-sm text-gray-600">
            <li className="flex gap-2"><span>•</span>3 switches Cisco (simulateur Packet Tracer, ou switches réels)</li>
            <li className="flex gap-2"><span>•</span>PC clients dans différents VLANs</li>
            <li className="flex gap-2"><span>•</span>Plan d'adressage fourni</li>
            <li className="flex gap-2"><span>•</span>Logiciel de supervision SNMP (SNMPwalk, SolarWinds, etc.)</li>
          </ul>
        </div>

        <Phase number={1} title="Préparation">
          <Steps items={[
            "Identifier les VLANs nécessaires : VLAN 10 (Informatique), VLAN 20 (RH), VLAN 30 (Comptabilité) — vous pouvez utiliser vos propres numéros",
            "Planifier les connexions inter-switches et les ports trunk",
            "Étudier le schéma réseau proposé",
          ]} />
        </Phase>

        <Phase number={2} title="Configuration réseau — VLANs, Trunks et STP">
          <CodeBlock code={`! Créer les VLANs sur chaque switch
Switch(config)# vlan 10
Switch(config-vlan)# name Informatique
Switch(config)# vlan 20
Switch(config-vlan)# name RH
Switch(config)# vlan 30
Switch(config-vlan)# name Comptabilite

! Ports d'accès
Switch(config)# interface Fa0/1
Switch(config-if)# switchport mode access
Switch(config-if)# switchport access vlan 10

! Ports Trunk (802.1Q) entre switches
Switch(config)# interface Gi0/1
Switch(config-if)# switchport mode trunk
Switch(config-if)# switchport trunk encapsulation dot1q

! Activer Rapid PVST+ et désigner un switch root
Switch(config)# spanning-tree mode rapid-pvst
Switch(config)# spanning-tree vlan 10,20,30 root primary`} language="cisco" />
        </Phase>

        <Phase number={3} title="Sécurisation couche 2">
          <CodeBlock code={`! BPDU Guard sur les ports d'accès (protège contre les faux switches)
Switch(config)# interface range Fa0/1-24
Switch(config-if-range)# spanning-tree portfast
Switch(config-if-range)# spanning-tree bpduguard enable

! DHCP Snooping
Switch(config)# ip dhcp snooping
Switch(config)# ip dhcp snooping vlan 10,20,30
! Marquer les ports vers le serveur DHCP comme trusted
Switch(config)# interface Gi0/1
Switch(config-if)# ip dhcp snooping trust

! Dynamic ARP Inspection (DAI)
Switch(config)# ip arp inspection vlan 10,20,30
Switch(config)# interface Gi0/1
Switch(config-if)# ip arp inspection trust`} language="cisco" />
          <Steps items={[
            "Vérifiez BPDU Guard : <code class='bg-gray-100 px-1 rounded text-xs'>show spanning-tree detail | include BPDU</code>",
            "Vérifiez DHCP Snooping : <code class='bg-gray-100 px-1 rounded text-xs'>show ip dhcp snooping binding</code>",
            "Vérifiez DAI : <code class='bg-gray-100 px-1 rounded text-xs'>show ip arp inspection vlan 10</code>",
          ]} />
          <Warning>
            Si DHCP Snooping est activé sans marquer le port vers le serveur DHCP comme <strong>trusted</strong>, les clients ne pourront pas obtenir d'adresse IP.
          </Warning>
        </Phase>

        <Phase number={4} title="Supervision SNMPv2c">
          <CodeBlock code={`! Configurer SNMPv2c sur les switches
Switch(config)# snmp-server community public RO
Switch(config)# snmp-server community private RW
Switch(config)# snmp-server host 192.168.10.100 version 2c public
Switch(config)# snmp-server enable traps

! Vérification
Switch# show snmp
Switch# show snmp community`} language="cisco" />
          <Steps items={[
            "Configurez l'IP du serveur SNMP (SNMPwalk ou SolarWinds) : 192.168.10.100",
            "Effectuez des tests de supervision : statut des interfaces, erreurs, trafic",
            "Vérifiez les alertes reçues lors de la désactivation d'une interface",
          ]} />
          <Tip>
            Pour tester avec SNMPwalk depuis un PC Linux : <code>snmpwalk -v2c -c public 192.168.10.1 .1.3.6.1.2.1.1.1.0</code>
          </Tip>
        </Phase>

        <Phase number={5} title="Tests et rapport">
          <Steps items={[
            "Tester la connectivité entre VLANs (via un routeur ou Switch L3)",
            "Capturer les configurations : <code class='bg-gray-100 px-1 rounded text-xs'>show running-config</code>",
            "Rédiger un rapport complet avec : configurations, résultats des tests, captures d'écran et recommandations",
          ]} />
          <InfoTable
            headers={["Commande de vérification", "Objectif"]}
            rows={[
              ["show vlan brief", "Vérifier les VLANs créés et leurs ports"],
              ["show interfaces trunk", "Vérifier les ports trunk actifs"],
              ["show spanning-tree vlan 10", "Vérifier le switch root et l'état STP"],
              ["show ip dhcp snooping binding", "Voir les baux DHCP validés"],
              ["show ip arp inspection vlan 10", "Statistiques DAI"],
              ["show snmp", "État de la configuration SNMP"],
            ]}
          />
        </Phase>

        <Checklist items={[
          "Les VLANs 10, 20, 30 sont créés et les ports correctement assignés",
          "Les trunks 802.1Q sont actifs entre les switches",
          "Rapid PVST+ est actif et le switch root est désigné",
          "BPDU Guard est actif sur les ports d'accès",
          "DHCP Snooping et DAI sont configurés et fonctionnels",
          "Le serveur SNMP reçoit des données (interfaces, trafic)",
          "Le rapport est rédigé avec toutes les captures",
        ]} />
      </TpSection>

      {/* TP 2 */}
      <TpSection number="Module 2" title="Optimisation réseau multi-switches : EtherChannel et ACLs" duration="2h">
        <Tip>
          <strong>Contexte :</strong> L'entreprise MOUNDZEKI tech constate des lenteurs et souhaite optimiser la bande passante entre ses switches (EtherChannel LACP), renforcer la sécurité avec des ACLs et configurer un Spanning Tree stable.
        </Tip>

        <Phase number={1} title="Analyse initiale">
          <Steps items={[
            "Lire le cahier des charges fourni",
            "Identifier les besoins en optimisation (quels liens sont saturés ?)",
            "Diagnostiquer l'état initial du réseau : <code class='bg-gray-100 px-1 rounded text-xs'>show interfaces | show spanning-tree | show etherchannel summary</code>",
            "Si le réseau n'est pas fourni, construisez-le selon le plan d'adressage",
          ]} />
        </Phase>

        <Phase number={2} title="Mise en place de l'EtherChannel (LACP)">
          <CodeBlock code={`! Sur Switch 1 (mode active)
Switch1(config)# interface range Gi0/1-2
Switch1(config-if-range)# channel-group 1 mode active
Switch1(config-if-range)# channel-protocol lacp

! Sur Switch 2 (mode passive)
Switch2(config)# interface range Gi0/1-2
Switch2(config-if-range)# channel-group 1 mode passive
Switch2(config-if-range)# channel-protocol lacp

! Vérification
Switch1# show etherchannel summary
Switch1# show etherchannel detail`} language="cisco" />
          <InfoTable
            headers={["Mode LACP", "Comportement"]}
            rows={[
              ["active", "Initie la négociation LACP — à configurer sur un côté au minimum"],
              ["passive", "Répond à la négociation LACP — ne l'initie pas"],
              ["on", "Force l'agrégation sans négociation — déconseillé"],
            ]}
          />
          <Tip>
            Après configuration, <code>show etherchannel summary</code> doit afficher <strong>P (bundled in port-channel)</strong> pour chaque interface agrégée. Si vous voyez (I) Independent, vérifiez que les interfaces ont les mêmes caractéristiques des deux côtés (vitesse, duplex, VLAN).
          </Tip>
        </Phase>

        <Phase number={3} title="Sécurisation STP — Root Guard et Loop Guard">
          <CodeBlock code={`! Redéfinir le switch root pour les VLANs
Switch1(config)# spanning-tree vlan 10,20,30 root primary
Switch1(config)# spanning-tree vlan 10,20,30 root secondary  ! sur le switch de secours

! Root Guard sur les uplinks secondaires (empêche un switch non autorisé de devenir root)
Switch2(config)# interface Gi0/3
Switch2(config-if)# spanning-tree guard root

! Loop Guard sur les liens redondants (empêche les boucles si BPDU cessent d'arriver)
Switch1(config)# interface Gi0/2
Switch1(config-if)# spanning-tree guard loop

! Vérification
Switch# show spanning-tree detail | include Root Guard
Switch# show spanning-tree inconsistentports`} language="cisco" />
          <Warning>
            N'activez <strong>jamais</strong> Root Guard et Loop Guard simultanément sur la même interface — ils s'excluent mutuellement.
          </Warning>
        </Phase>

        <Phase number={4} title="Application des ACLs — Sécurisation inter-VLAN">
          <CodeBlock code={`! Exemple : interdire l'accès du VLAN RH (20) au VLAN Informatique (10)
! IP VLAN RH : 192.168.20.0/24 | IP VLAN Informatique : 192.168.10.0/24

Router(config)# ip access-list extended RESTRICT_RH_TO_INFO
Router(config-ext-nacl)# deny ip 192.168.20.0 0.0.0.255 192.168.10.0 0.0.0.255
Router(config-ext-nacl)# permit ip any any

! Appliquer sur l'interface VLAN 20 (entrée)
Router(config)# interface vlan 20
Router(config-if)# ip access-group RESTRICT_RH_TO_INFO in

! Restreindre SSH : autorisé seulement depuis VLAN Informatique
Router(config)# ip access-list standard SSH_ACCESS
Router(config-std-nacl)# permit 192.168.10.0 0.0.0.255
Router(config-std-nacl)# deny any log

Router(config)# line vty 0 15
Router(config-line)# access-class SSH_ACCESS in

! Vérification
Router# show ip access-lists
Router# show running-config | include access-group`} language="cisco" />
          <Steps items={[
            "Testez l'impact des ACLs : ping depuis VLAN RH vers VLAN Informatique (doit être bloqué)",
            "Testez SSH depuis VLAN Informatique (doit fonctionner) et depuis VLAN RH (doit être refusé)",
          ]} />
          <Tip>
            Les ACLs standard filtre sur l'IP source uniquement → à appliquer le plus proche de la destination.<br />
            Les ACLs étendues filtrent sur source + destination + protocole → à appliquer le plus proche de la source.
          </Tip>
        </Phase>

        <Phase number={5} title="Validation et rapport">
          <Steps items={[
            "Tests de connectivité : ping et tracert entre VLANs",
            "Vérifier les performances EtherChannel : <code class='bg-gray-100 px-1 rounded text-xs'>show interfaces port-channel 1 | show etherchannel load-balance</code>",
            "Observer le réseau : <code class='bg-gray-100 px-1 rounded text-xs'>show interfaces | show port-channel</code>",
            "Rédiger le rapport final avec toutes les captures et commentaires",
          ]} />
          <InfoTable
            headers={["Commande", "Objectif"]}
            rows={[
              ["show etherchannel summary", "Statut des agrégats LACP"],
              ["show spanning-tree vlan 10", "Switch root, ports bloqués"],
              ["show ip access-lists", "Compteurs des règles ACL (hits)"],
              ["show interfaces port-channel 1", "Débit agrégé EtherChannel"],
              ["ping 192.168.10.1 source vlan 20", "Test connectivité inter-VLAN"],
              ["traceroute 192.168.10.1", "Chemin pris par les paquets"],
            ]}
          />
        </Phase>

        <Checklist items={[
          "show etherchannel summary affiche P (bundled) pour les interfaces LACP",
          "Le switch root est correctement désigné (show spanning-tree vlan 10)",
          "Root Guard et Loop Guard sont actifs sur les bons ports",
          "L'ACL bloque l'accès VLAN RH → VLAN Informatique (ping échoue)",
          "SSH n'est accessible que depuis le VLAN Informatique",
          "Le rapport est fourni avec toutes les configurations et captures",
        ]} />
      </TpSection>

      {/* Astuces générales */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Astuces générales Cisco</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <p className="text-sm font-semibold text-amber-800 mb-2">Sauvegarder la configuration</p>
            <CodeBlock code={`Switch# copy running-config startup-config
! ou
Switch# wr`} language="cisco" />
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <p className="text-sm font-semibold text-blue-800 mb-2">Effacer et recommencer</p>
            <CodeBlock code={`Switch# erase startup-config
Switch# delete vlan.dat
Switch# reload`} language="cisco" />
          </div>
          <div className="bg-green-50 border border-green-200 rounded-xl p-4">
            <p className="text-sm font-semibold text-green-800 mb-2">Debug VLAN & Trunk</p>
            <CodeBlock code={`Switch# show vlan brief
Switch# show interfaces trunk
Switch# show mac address-table vlan 10`} language="cisco" />
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
            <p className="text-sm font-semibold text-purple-800 mb-2">Debug ACLs</p>
            <CodeBlock code={`Router# show ip access-lists
! Les compteurs (hits) permettent de vérifier
! si les règles ACL sont bien atteintes`} language="cisco" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Déblocage rapide (si ça ne marche pas)</h2>
        <ul className="space-y-2 text-sm text-gray-700 mb-4">
          <li>1. Vérifier les VLANs et l'affectation des ports : <span className="font-mono">show vlan brief</span></li>
          <li>2. Vérifier les trunks : <span className="font-mono">show interfaces trunk</span></li>
          <li>3. Vérifier STP et le root : <span className="font-mono">show spanning-tree vlan 10</span></li>
          <li>4. Vérifier EtherChannel : <span className="font-mono">show etherchannel summary</span></li>
          <li>5. Vérifier ACLs et compteurs : <span className="font-mono">show ip access-lists</span></li>
        </ul>
        <Warning>
          Si un trunk ne passe pas, comparez la configuration des deux côtés (mode trunk, VLANs autorisés, encapsulation) avant de modifier STP ou les ACLs.
        </Warning>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Annexes et ressources en ligne</h2>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>
            <a className="text-indigo-600 hover:underline" href="https://www.cisco.com/c/en/us/support/docs/lan-switching/etherchannel/12023-4.html" target="_blank" rel="noreferrer">
              Cisco - Understand EtherChannel Load Balance and Redundancy
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://www.cisco.com/c/en/us/support/index.html" target="_blank" rel="noreferrer">
              Cisco Technical Support and Documentation Portal
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://www.rfc-editor.org/rfc/rfc3411" target="_blank" rel="noreferrer">
              RFC 3411 - SNMP Management Frameworks
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://www.rfc-editor.org/rfc/rfc2328" target="_blank" rel="noreferrer">
              RFC 2328 - OSPF Version 2 (référence routage inter-VLAN)
            </a>
          </li>
        </ul>
      </div>
    </WikiLayout>
  );
}
