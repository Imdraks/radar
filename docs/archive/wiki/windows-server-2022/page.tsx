import {
  WikiLayout, TpSection, Phase, Steps, CodeBlock, Tip, Warning, Checklist, InfoTable,
} from "../components";

export const metadata = {
  title: "Guide Windows Server 2022 GUI",
  robots: { index: false, follow: false },
};

export default function WS2022Page() {
  return (
    <WikiLayout
      title="Windows Server 2022 — Interface Graphique"
      subtitle="Modules 1 à 4 · AD, sécurité réseau, haute disponibilité"
      description="Infrastructure AD DS, DNS, DHCP, VPN RADIUS, DNSSEC, Wi-Fi WPA2-Enterprise, 802.1X, GPO et haute disponibilité — 100% GUI, sans ligne de commande."
      color="from-violet-600 to-purple-700"
    >

      {/* Infos communes */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-3">Informations communes</h2>
        <InfoTable
          headers={["Paramètre", "Valeur"]}
          rows={[
            ["Domaine", "entreprise.local"],
            ["Mot de passe serveur", "Entreprise2026"],
            ["Utilisateur admin", "amartin@entreprise.local"],
            ["Mot de passe user Wifi", "tmoundzeki@entreprise.local : Dodo2026+"],
            ["Plage DHCP", "192.168.10.100 – 192.168.10.200"],
            ["IP DC1", "192.168.10.1"],
            ["IP DC2", "192.168.10.2"],
          ]}
        />
        <Tip>
          Ce document présente toutes les étapes <strong>exclusivement via l'interface graphique (GUI)</strong> de Windows Server 2022. Aucune ligne de commande n'est utilisée.
        </Tip>
      </div>

      {/* TP 1 */}
      <TpSection number="Module 1" title="Infrastructure de base : AD DS, DNS, DHCP, VPN RADIUS" duration="4h">

        <Phase number={1} title="Installation et configuration AD DS">
          <Steps items={[
            "<strong>Gestionnaire de serveur → Gérer → Ajouter des rôles et fonctionnalités</strong>",
            "Choisir <em>Installation basée sur un rôle ou une fonctionnalité</em> → Suivant",
            "Cocher <strong>Services de domaine Active Directory (AD DS)</strong> → Ajouter des fonctionnalités → Installer",
            "Cliquer sur la notification jaune → <strong>Promouvoir ce serveur en contrôleur de domaine</strong>",
            "Choisir <em>Ajouter une nouvelle forêt</em> → Nom de domaine racine : <strong>entreprise.local</strong>",
            "Niveau fonctionnel : Windows Server 2016 | Cocher Serveur DNS et Catalogue global",
            "Mot de passe DSRM : <strong>P@ssw0rd!DSRM</strong> (le noter précieusement)",
            "Cliquer Installer — Le serveur redémarre automatiquement",
          ]} />
          <Tip>
            Après redémarrage : Gestionnaire de serveur → Outils → <strong>Utilisateurs et ordinateurs Active Directory</strong> → vérifiez que le domaine <code>entreprise.local</code> apparaît dans l'arborescence.
          </Tip>
        </Phase>

        <Phase number={2} title="Configuration DNS intégré AD">
          <p className="text-sm text-gray-600">Chemin : <strong>Gestionnaire de serveur → Outils → DNS</strong> (ou taper <code>dnsmgmt.msc</code> dans Exécuter)</p>
          <Steps items={[
            "Vérifiez que la zone <strong>entreprise.local</strong> est déjà présente dans Zones de recherche directe",
            "Clic droit sur Zones de recherche inversée → Nouvelle zone",
            "Type : Principale, intégrée AD | Réseau IPv4 : <strong>192.168.10</strong> | Mises à jour : sécurisées uniquement",
            "Test DNS : clic droit sur le serveur → Lancer nslookup → taper <code>entreprise.local</code>",
          ]} />
        </Phase>

        <Phase number={3} title="Structure AD — UO, utilisateurs et groupes">
          <p className="text-sm text-gray-600 mb-2">Chemin : <strong>Gestionnaire de serveur → Outils → Utilisateurs et ordinateurs Active Directory</strong></p>
          <Steps items={[
            "Clic droit sur entreprise.local → Nouveau → Unité d'organisation : créez <strong>OU=Utilisateurs</strong>, <strong>OU=Administrateurs</strong>, <strong>OU=Employes</strong>, <strong>OU=VPN_Autorises</strong>, <strong>OU=Ordinateurs</strong>",
            "Créez l'utilisateur <strong>Alice Martin</strong> (amartin@entreprise.local) dans OU=Administrateurs — Mot de passe : P@ssw0rd!",
            "Créez l'utilisateur <strong>steve pierre</strong> dans OU=Employes — Mot de passe : Pentreprise2026",
            "Créez le groupe <strong>VPN_Autorises</strong> dans OU=VPN_Autorises (Étendue : Globale, Type : Sécurité)",
            "Double-clic sur le groupe → Membres → Ajouter → sélectionnez l'utilisateur <code>cvpn</code>",
          ]} />
        </Phase>

        <Phase number={4} title="Configuration DHCP">
          <Steps items={[
            "Gestionnaire de serveur → Gérer → Ajouter des rôles → cocher <strong>Serveur DHCP</strong> → Installer",
            "Notification jaune → <strong>Terminer la configuration DHCP</strong> → Valider",
            "Gestionnaire de serveur → Outils → DHCP → IPv4 → clic droit → <strong>Nouvelle étendue</strong>",
          ]} />
          <InfoTable
            headers={["Paramètre", "Valeur"]}
            rows={[
              ["Nom de l'étendue", "LAN_Entreprise"],
              ["Plage d'adresses", "192.168.10.100 → 192.168.10.200"],
              ["Masque", "255.255.255.0"],
              ["Routeur (passerelle)", "192.168.10.1"],
              ["Serveur DNS", "192.168.10.1"],
              ["Suffixe DNS", "entreprise.local"],
            ]}
          />
          <Tip>
            Sur un poste client : Panneau de configuration → Centre Réseau → Modifier les paramètres de la carte → désactivez/réactivez la carte pour forcer le renouvellement du bail.
          </Tip>
        </Phase>

        <Phase number={5} title="Serveur RADIUS (NPS) pour VPN">
          <Steps items={[
            "Ajouter des rôles → <strong>Services de stratégie et d'accès réseau (NPAS)</strong> → cocher Serveur NPS → Installer",
            "Console NPS → clic droit sur NPS (local) → <strong>Inscrire le serveur dans Active Directory</strong>",
          ]} />
          <p className="text-sm font-medium text-gray-700 mt-3">Stratégie de demande de connexion</p>
          <InfoTable
            headers={["Champ", "Valeur"]}
            rows={[
              ["Nom", "Demandes VPN"],
              ["Condition", "Type de port NAS = Virtual (VPN)"],
              ["Action", "Authentifier les demandes sur ce serveur"],
            ]}
          />
          <p className="text-sm font-medium text-gray-700 mt-3">Stratégie réseau — utilisateurs VPN autorisés</p>
          <InfoTable
            headers={["Champ", "Valeur"]}
            rows={[
              ["Nom", "VPN_Autorises — Priorité : 1"],
              ["Condition", "Groupes Windows = VPN_Autorises"],
              ["Autorisation", "Accès accordé"],
              ["Authentification", "MS-CHAPv2"],
            ]}
          />
          <Steps items={[
            "Stratégie réseau → Nouveau → <strong>VPN_Refus</strong> (Priorité 2, aucune condition) → Accès refusé",
            "Ajouter des rôles → <strong>Accès à distance</strong> → Routage → Installer",
            "Console RRAS → clic droit sur le serveur → Configurer et activer RRAS → Accès à distance (VPN)",
            "Propriétés → Sécurité → Fournisseur d'authentification : <strong>Authentification RADIUS</strong> → Serveur : 127.0.0.1, Port 1812, Secret : <code>VpnRadiusSecret123!</code>",
          ]} />
        </Phase>

        <Phase number={6} title="Serveur IIS avec SSO">
          <Steps items={[
            "Ajouter des rôles → <strong>Serveur Web (IIS)</strong> → cocher Authentification Windows, ASP.NET 4.x → Installer",
            "Créez le dossier <code>C:\\inetpub\\portail_vpn\\</code> dans l'Explorateur",
            "Gestionnaire IIS → Sites → clic droit → <strong>Ajouter un site Web</strong> : Portail_VPN | Chemin : portail_vpn | Port : <strong>8080</strong>",
            "Sélectionnez le site → Authentification → <strong>Désactivez</strong> Authentification anonyme → <strong>Activez</strong> Authentification Windows",
          ]} />
          <Tip>
            Depuis un poste joint au domaine, ouvrez <code>http://192.168.10.1:8080</code> — l'utilisateur ne doit PAS être invité à saisir ses identifiants (SSO via Kerberos/NTLM).
          </Tip>
        </Phase>

        <Checklist items={[
          "Le domaine entreprise.local apparaît dans Utilisateurs et ordinateurs AD",
          "La zone DNS entreprise.local est active (icône verte)",
          "Le poste client obtient une IP dans la plage 192.168.10.100-200",
          "La connexion VPN s'authentifie via RADIUS (ID 6272 dans l'Observateur d'événements)",
          "http://localhost:8080 affiche la page IIS sans demande de mot de passe (SSO)",
        ]} />
      </TpSection>

      {/* TP 2 */}
      <TpSection number="Module 2" title="Sécurisation DNS (DNSSEC) et Wi-Fi WPA2-Enterprise" duration="4h">

        <Phase number={1} title="DNS avancé — Enregistrements A, CNAME, PTR">
          <Steps items={[
            "Gestionnaire DNS → Zones de recherche directe → entreprise.local",
            "Clic droit → <strong>Nouvel hôte (A)</strong> : web = 192.168.10.1 | vpn = 192.168.10.1 | wifi = 192.168.10.50 (cocher 'Créer l'enregistrement PTR')",
            "Clic droit → <strong>Nouvel alias (CNAME)</strong> : www → web.entreprise.local | portail → web.entreprise.local",
          ]} />
        </Phase>

        <Phase number={2} title="Activation de DNSSEC">
          <Steps items={[
            "Clic droit sur la zone <strong>entreprise.local</strong> → DNSSEC → <strong>Signer la zone</strong>",
            "Choisir <em>Utiliser les paramètres par défaut</em> → Algorithme : RSASHA256 → Suivant → Terminer",
            "Appuyez sur <strong>F5</strong> pour actualiser — les types DNSKEY, RRSIG et NSEC doivent apparaître",
          ]} />
          <InfoTable
            headers={["Type d'enregistrement", "Rôle"]}
            rows={[
              ["DNSKEY", "Clés publiques KSK et ZSK"],
              ["RRSIG", "Signature de chaque enregistrement"],
              ["NSEC", "Preuve d'absence d'un nom"],
            ]}
          />
          <Tip>
            DNSSEC sécurise l'<strong>intégrité</strong> DNS, pas la confidentialité — les réponses sont signées numériquement mais pas chiffrées.
          </Tip>
        </Phase>

        <Phase number={3} title="NPS pour Wi-Fi WPA2-Enterprise">
          <Steps items={[
            "Console NPS → Clients RADIUS → Nouveau : <strong>Point_Acces_WiFi</strong> | IP : 192.168.10.50 | Secret : <code>WifiRadiusSecret456!</code>",
            "Stratégies réseau → Nouveau → <strong>WiFi_Enterprise</strong>",
            "Conditions : Type de port NAS = Sans fil — IEEE 802.11 | Groupes Windows = Domain Users",
            "Onglet Contraintes → Méthode EAP : <strong>PEAP (Protected EAP)</strong> avec MS-CHAPv2",
            "Ajouter des rôles → <strong>Services de certificats AD (AD CS)</strong> → Enterprise Root CA → Installer et configurer",
          ]} />
          <InfoTable
            headers={["Paramètre hostapd (Ubuntu)", "Valeur"]}
            rows={[
              ["ssid", "Entreprise-WiFi"],
              ["wpa", "2"],
              ["wpa_key_mgmt", "WPA-EAP"],
              ["rsn_pairwise", "CCMP"],
              ["auth_server_addr", "192.168.10.1"],
              ["auth_server_port", "1812"],
              ["auth_server_shared_secret", "WifiRadiusSecret456!"],
            ]}
          />
        </Phase>

        <Phase number={4} title="Connexion Wi-Fi depuis un client Windows">
          <Steps items={[
            "Importez le certificat CA : Exécuter → <code>certmgr.msc</code> → Autorités de certification racines de confiance → Importer le fichier .CER",
            "Icône Wi-Fi dans la barre des tâches → sélectionnez <strong>Entreprise-WiFi</strong> → Connecter",
            "Saisissez <code>amartin@entreprise.local</code> et le mot de passe",
            "Validez le certificat du serveur NPS lorsqu'une fenêtre de confirmation s'affiche",
          ]} />
          <Tip>
            Vérifiez dans l'Observateur d'événements → Journaux Windows → Sécurité : ID <strong>6272</strong> (connexion Wi-Fi accordée).
          </Tip>
        </Phase>

        <Checklist items={[
          "La zone entreprise.local affiche un cadenas (DNSSEC activé)",
          "Les enregistrements DNSKEY, RRSIG et NSEC sont visibles (F5)",
          "Le client RADIUS 'Point_Acces_WiFi' est créé dans NPS",
          "La connexion au réseau Entreprise-WiFi réussit avec amartin@entreprise.local",
          "ID 6272 apparaît dans l'Observateur d'événements → Sécurité",
        ]} />
      </TpSection>

      {/* TP 3 */}
      <TpSection number="Module 3" title="Authentification 802.1X Filaire et GPO" duration="4h">

        <Phase number={1} title="NPS pour 802.1X filaire — Client RADIUS Switch">
          <Steps items={[
            "Console NPS → Clients RADIUS → Nouveau : <strong>Switch_Principal</strong> | IP : 192.168.10.60 | Secret : <code>Switch8021xSecret!</code>",
            "Stratégies réseau → Nouveau → <strong>802.1X_Filaire</strong>",
            "Conditions : Type de port NAS = Ethernet | Groupes Windows = Domain Computers",
            "Méthode EAP : PEAP avec MS-CHAPv2",
          ]} />
          <p className="text-sm font-medium text-gray-700 mt-3">Attributs RADIUS pour l'affectation VLAN</p>
          <InfoTable
            headers={["Attribut", "Valeur"]}
            rows={[
              ["Tunnel-Type", "VLAN (valeur 13)"],
              ["Tunnel-Medium-Type", "802 (valeur 6)"],
              ["Tunnel-Private-Group-ID", "10"],
            ]}
          />
        </Phase>

        <Phase number={2} title="Client Windows 802.1X filaire">
          <Steps items={[
            "Panneau de configuration → Centre Réseau → Modifier les paramètres de la carte → clic droit sur Ethernet → Propriétés",
            "Onglet <strong>Authentification</strong> → cocher <strong>Activer l'authentification IEEE 802.1X</strong>",
            "Méthode : <strong>Microsoft : EAP protégé (PEAP)</strong>",
            "Paramètres : Valider le certificat serveur → AC entreprise-CA | Méthode interne : EAP-MSCHAP v2",
            "Cocher <em>Utiliser automatiquement mon nom et mot de passe de connexion Windows</em>",
          ]} />
          <Warning>
            Le service <strong>Connexion automatique câblée (Dot3Svc)</strong> doit être démarré et configuré en démarrage automatique. Vérifiez dans <code>services.msc</code>.
          </Warning>
        </Phase>

        <Phase number={3} title="GPO — Stratégies de groupe">
          <p className="text-sm text-gray-600 mb-2">Chemin : Gestionnaire de serveur → Outils → <strong>Gestion des stratégies de groupe</strong> (gpmc.msc)</p>

          <p className="text-sm font-medium text-gray-700 mt-3">GPO_Firewall_Entreprise (liée à OU=Postes_Travail)</p>
          <Steps items={[
            "Clic droit sur OU=Postes_Travail → Créer un objet GPO → Nom : <strong>GPO_Firewall_Entreprise</strong>",
            "Clic droit → Modifier → Configuration ordinateur → Paramètres de sécurité → <strong>Pare-feu Windows avec fonctions avancées</strong>",
          ]} />
          <InfoTable
            headers={["Règle", "Port/Protocole", "Source", "Action"]}
            rows={[
              ["RDP entrant", "TCP 3389", "192.168.10.0/24", "Autoriser"],
              ["ICMPv4 entrant", "ICMPv4 Echo Request", "192.168.10.0/24", "Autoriser"],
              ["SMB entrant", "TCP 445", "192.168.10.1 uniquement", "Autoriser"],
              ["Tout le reste", "—", "Tous", "Bloquer"],
            ]}
          />

          <p className="text-sm font-medium text-gray-700 mt-3">GPO_Certificats — Inscription automatique</p>
          <p className="text-sm text-gray-600">Configuration ordinateur → Paramètres de sécurité → Stratégies de clé publique → Inscription automatique → <strong>Activé</strong>, cocher les 2 options de renouvellement.</p>

          <p className="text-sm font-medium text-gray-700 mt-3">GPO_Restrictions_Reseau</p>
          <Steps items={[
            "Désactiver LLMNR : Configuration ordinateur → Modèles d'administration → Réseau → Client DNS → <em>Désactiver la résolution de noms de multidiffusion</em>",
            "Désactiver NetBIOS via les préférences de registre : HKLM\\SYSTEM\\CurrentControlSet\\Services\\NetBT\\Parameters → NetbiosOptions = 2",
            "Désactiver SMBv1 : HKLM\\SYSTEM\\CurrentControlSet\\Services\\LanmanServer\\Parameters → SMB1 = 0",
          ]} />
          <CodeBlock code={`# Sur un poste client, forcer l'application des GPO
gpupdate /force`} />
        </Phase>

        <Checklist items={[
          "Le switch/802.1X authentifie les postes via NPS (ID 6272 dans les logs)",
          "Les règles GPO_Firewall_Entreprise apparaissent en grisé dans le Pare-feu Windows avancé",
          "L'inscription automatique de certificats s'applique (gpresult /r)",
          "LLMNR est désactivé sur les postes clients",
        ]} />
      </TpSection>

      {/* TP 4 */}
      <TpSection number="Module 4" title="Haute Disponibilité : DHCP Failover et infrastructure résiliente" duration="4h">

        <Phase number={1} title="Second contrôleur de domaine (DC2)">
          <Steps items={[
            "Sur DC2 : configurer l'IP fixe 192.168.10.2, Masque 255.255.255.0, DNS = 192.168.10.1",
            "Paramètres → Système → À propos → Renommer ce PC → Membre du domaine : <strong>entreprise.local</strong>",
            "Gestionnaire de serveur → Ajouter des rôles → AD DS → Installer",
            "Notification jaune → <strong>Promouvoir ce serveur en contrôleur de domaine</strong>",
            "Choisir <em>Ajouter un contrôleur de domaine à un domaine existant</em> → entreprise.local | Cocher DNS, Catalogue global | Mot de passe DSRM : P@ssw0rd!DSRM",
          ]} />
          <Steps items={[
            "Vérification réplication : Sites et services AD → DC2 doit apparaître dans Default-First-Site-Name",
            "Créez un utilisateur test sur DC1 et vérifiez qu'il apparaît sur DC2 en quelques secondes",
            "Forcer la réplication : clic droit sur la connexion → <strong>Répliquer maintenant</strong>",
          ]} />
        </Phase>

        <Phase number={2} title="DHCP Failover">
          <Steps items={[
            "Sur DC2 : Ajouter des rôles → Serveur DHCP → Installer → configuration post-déploiement → Valider",
            "Ne pas créer d'étendue sur DC2 — elle sera répliquée depuis DC1",
            "Sur DC1 : Console DHCP → IPv4 → clic droit sur l'étendue LAN_Entreprise → <strong>Configurer le basculement</strong>",
          ]} />
          <InfoTable
            headers={["Paramètre", "Valeur"]}
            rows={[
              ["Serveur partenaire", "192.168.10.2 (DC2)"],
              ["Mode de basculement", "Équilibrage de charge (Load Balance)"],
              ["Répartition de charge", "50% / 50%"],
              ["MCLT", "1 heure"],
              ["Secret partagé", "DhcpFailoverSecret!"],
            ]}
          />
          <Tip>
            MCLT (Max Client Lead Time) : si DC1 tombe, DC2 peut accorder des baux pour une durée maximale de MCLT (1 heure) sans risque de conflit d'adresses. Après cette durée, DC2 prend le contrôle total.
          </Tip>
        </Phase>

        <Phase number={3} title="Haute disponibilité NPS pour VPN">
          <Steps items={[
            "Sur DC1 : Console NPS → clic droit NPS (local) → <strong>Exporter la configuration</strong> (inclure les secrets partagés) → enregistrer nps-config.xml",
            "Copiez nps-config.xml sur DC2 via le réseau",
            "Sur DC2 : Console NPS → clic droit NPS (local) → <strong>Importer la configuration</strong>",
          ]} />
          <p className="text-sm font-medium text-gray-700 mt-3">Basculement RADIUS dans RRAS</p>
          <InfoTable
            headers={["Serveur", "Primaire", "Secondaire"]}
            rows={[
              ["DC1", "127.0.0.1 (lui-même)", "192.168.10.2 (DC2)"],
              ["DC2", "127.0.0.1 (lui-même)", "192.168.10.1 (DC1)"],
            ]}
          />
          <p className="text-sm font-medium text-gray-700 mt-3">Round Robin DNS pour VPN</p>
          <Steps items={[
            "Gestionnaire DNS → entreprise.local → créez 2 enregistrements A avec le même nom <strong>vpn</strong> : IP 192.168.10.1 et IP 192.168.10.2",
            "Le DNS alternera automatiquement entre les deux adresses (Round Robin)",
          ]} />
        </Phase>

        <Phase number={4} title="Tests de basculement">
          <p className="text-sm font-medium text-gray-700">Test 1 — Panne DHCP primaire</p>
          <Steps items={[
            "Sur DC1 : services.msc → <strong>Serveur DHCP</strong> → Arrêter",
            "Sur un poste client : désactivez/réactivez la carte réseau",
            "Console DHCP sur DC2 : l'adresse attribuée doit apparaître dans Baux d'adresses",
            "Redémarrez le service DHCP sur DC1 et vérifiez la re-synchronisation",
          ]} />
          <p className="text-sm font-medium text-gray-700 mt-3">Test 2 — Panne NPS</p>
          <Steps items={[
            "services.msc → <strong>Serveur NPS (IAS)</strong> → Arrêter",
            "Tentez une connexion VPN → elle doit basculer sur le NPS secondaire",
            "Vérifiez ID 6272 dans l'Observateur d'événements sur DC2",
          ]} />
          <p className="text-sm font-medium text-gray-700 mt-3">Test 3 — Panne DC1 complète</p>
          <Steps items={[
            "Éteignez DC1 depuis l'hyperviseur",
            "Vérifiez que l'authentification AD, DNS, DHCP, VPN et IIS fonctionnent tous via DC2",
          ]} />
          <InfoTable
            headers={["Service", "Journal", "IDs clés"]}
            rows={[
              ["DHCP Failover", "Applications et services → DHCP-Server", "20289, 20290, 20288"],
              ["Réplication AD", "Journaux Windows → Système → NTDS", "1791, 1394"],
              ["NPS", "Journaux Windows → Sécurité", "6272 (succès), 6273 (échec)"],
            ]}
          />
        </Phase>

        <div className="border-t border-gray-100 pt-5">
          <h3 className="font-semibold text-gray-800 mb-3">Points clés de validation</h3>
          <InfoTable
            headers={["Module", "Concept", "Point clé"]}
            rows={[
              ["Module 1", "Socle obligatoire", "Sans AD/DNS/DHCP fonctionnels, rien d'autre ne marche"],
              ["Module 2", "RADIUS = cœur", "Bien comprendre les stratégies réseau NPS et les clients RADIUS"],
              ["Module 2", "DNSSEC", "Sécurise l'intégrité DNS, pas la confidentialité"],
              ["Module 3", "802.1X", "Authentification AVANT accès réseau (port-based NAC)"],
              ["Module 4", "Load Balance ≠ Hot Standby", "En Load Balance, les deux serveurs DHCP répondent en parallèle"],
              ["Module 4", "MCLT", "Durée maximale de désaccord entre serveurs DHCP partenaires"],
            ]}
          />
        </div>

        <Checklist items={[
          "DC2 est promu contrôleur de domaine et réplique AD depuis DC1",
          "L'étendue LAN_Entreprise apparaît sur DC2 avec état 'Normal'",
          "Un poste client obtient une IP depuis DC2 quand DC1 est arrêté",
          "La connexion VPN bascule sur le NPS de DC2 (ID 6272 dans les logs de DC2)",
          "Toutes les fonctions critiques restent opérationnelles avec DC1 éteint",
        ]} />
      </TpSection>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Annexes et ressources en ligne</h2>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>
            <a className="text-indigo-600 hover:underline" href="https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview" target="_blank" rel="noreferrer">
              Microsoft Learn - Active Directory Domain Services overview
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://learn.microsoft.com/en-us/windows-server/networking/dns/dns-top" target="_blank" rel="noreferrer">
              Microsoft Learn - DNS on Windows Server
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://learn.microsoft.com/en-us/windows-server/networking/technologies/dhcp/dhcp-top" target="_blank" rel="noreferrer">
              Microsoft Learn - DHCP on Windows Server
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/best-practices-for-securing-active-directory" target="_blank" rel="noreferrer">
              Microsoft Learn - AD Security Best Practices
            </a>
          </li>
        </ul>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Déblocage rapide (si ça ne marche pas)</h2>
        <ul className="space-y-2 text-sm text-gray-700 mb-4">
          <li>1. Vérifier l'heure et la synchronisation NTP sur tous les serveurs (écarts de temps = authentification cassée)</li>
          <li>2. Vérifier la résolution DNS du domaine avant de diagnostiquer AD ou GPO</li>
          <li>3. Vérifier l'état des services AD DS, DNS, DHCP, NPS dans Services</li>
          <li>4. Vérifier les journaux Event Viewer pour les IDs critiques (DHCP, NPS, réplication AD)</li>
          <li>5. Tester d'abord localement sur le LAN, puis via VPN/Wi-Fi/802.1X</li>
        </ul>
        <InfoTable
          headers={["Vérification", "Où regarder"]}
          rows={[
            ["Réplication AD", "Active Directory Sites and Services + Event Viewer"],
            ["Attribution IP DHCP", "DHCP Console > Address Leases"],
            ["Authentification RADIUS", "Event Viewer > Security > IDs 6272/6273"],
            ["Résolution DNS", "DNS Manager + nslookup depuis un client"],
          ]}
        />
      </div>
    </WikiLayout>
  );
}
