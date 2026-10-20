import {
  WikiLayout, TpSection, Phase, Steps, CodeBlock, Tip, Warning, Checklist, InfoTable,
} from "../components";

export const metadata = {
  title: "Guide VoIP — Asterisk PJSIP",
  robots: { index: false, follow: false },
};

export default function VoIPPage() {
  return (
    <WikiLayout
      title="VoIP — Asterisk PJSIP"
      subtitle="Modules 1 à 4 · Déploiement, sécurité, supervision, QoS"
      description="Configuration et sécurisation PJSIP avec Asterisk 20+, déploiement Docker, supervision Zabbix/Grafana et optimisation QoS pour clients mobiles."
      color="from-blue-600 to-indigo-700"
    >

      {/* Paramètres communs */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-3">Paramètres communs à tous les modules</h2>
        <InfoTable
          headers={["Paramètre", "Valeur"]}
          rows={[
            ["IP Serveur Asterisk", "192.168.200.10/24"],
            ["VLAN", "VLAN 200"],
            ["OS / Asterisk", "Ubuntu 22.04 LTS + Asterisk 20+"],
            ["Port SIP UDP", "5060"],
            ["Port TLS", "5061"],
            ["Plage RTP", "10000 – 20000 (UDP)"],
            ["Endpoint 1", "1001 / Pass1001Secure2026!"],
            ["Endpoint 2", "1002 / Pass1002Secure2026!"],
          ]}
        />
      </div>

      {/* TP 1 */}
      <TpSection number="Module 1" title="Analyse et Sécurisation Infrastructure PJSIP" duration="2h">
        <Tip>
          Objectif : Configurer les endpoints PJSIP, capturer avec Wireshark, simuler des attaques sipvicious, implémenter TLS/SRTP/ICE et valider les métriques de performance.
        </Tip>

        <Phase number={1} title="Configuration PJSIP de base (UDP non sécurisé)">
          <CodeBlock code={`sudo nano /etc/asterisk/pjsip.conf`} />
          <CodeBlock code={`; ─── /etc/asterisk/pjsip.conf — TP1 ───────────────────────
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060
domain=192.168.200.10
local_net=192.168.200.0/24
external_media_address=192.168.200.10
external_signaling_address=192.168.200.10

[1001]
type=endpoint
transport=transport-udp       ; ← changer en transport-tls à l'Étape 4
context=from-internal
allow=!all,allow=ulaw,alaw,g729,g722,opus
auth=1001-auth
aors=1001-aor
force_rport=yes
rtp_symmetric=yes
direct_media=no
ice_support=no                ; ← passer à yes à l'Étape 4
dtmf_mode=rfc4733

[1001-auth]
type=auth
auth_type=userpass
realm=pjsip.ciel.ga
username=1001
password=Pass1001Secure2026!

[1001-aor]
type=aor
max_contacts=5
remove_existing=yes

; Répétez la même structure pour [1002] / [1002-auth] / [1002-aor]`} language="ini" />
          <CodeBlock code={`sudo nano /etc/asterisk/extensions.conf`} />
          <CodeBlock code={`[from-internal]
exten => 1001,1,NoOp(Appel vers 1001)
 same => n,Dial(PJSIP/1001,25,tTWrK)
 same => n,Voicemail(1001@u1)
 same => n,Hangup()
exten => 1002,1,NoOp(Appel vers 1002)
 same => n,Dial(PJSIP/1002,25,tTWrK)
 same => n,Voicemail(1002@u1)
 same => n,Hangup()
exten => 999,1,Playback(hello-world)
 same => n,Hangup()`} language="ini" />
          <CodeBlock code={`# Rechargement à chaud (recommandé)
sudo asterisk -r
*CLI> module reload res_pjsip.so
*CLI> pjsip reload
*CLI> dialplan reload

# Vérification
*CLI> pjsip show endpoints
*CLI> pjsip show transports`} />
        </Phase>

        <Phase number={2} title="Test fonctionnel + Capture Wireshark (UDP)">
          <InfoTable
            headers={["Zoiper", "Configuration"]}
            rows={[
              ["PC1 (compte 1001)", "Server: 192.168.200.10:5060 | User: 1001 | Transport: UDP"],
              ["PC2 (compte 1002)", "Server: 192.168.200.10:5060 | User: 1002 | Transport: UDP"],
            ]}
          />
          <Steps items={[
            "Vérifiez le statut Zoiper → icône verte 'Registered'",
            "Lancez Wireshark en sudo — Interface: eth0 ou vlan200",
            "Filtre de capture : <code class='bg-gray-100 px-1 rounded text-xs'>udp.port == 5060 or udp.portrange 10000-20000</code>",
            "Effectuez un appel PC1 → 1002 (> 30 secondes)",
            "Statistics > RTP > Stream : vérifiez Jitter < 20 ms, Loss 0 %",
          ]} />
          <Tip>
            Valeurs attendues : Latence &lt; 50 ms | Jitter &lt; 20 ms | Loss 0 %. Sauvegardez la capture : <code>pcap_tp1_nonsec.pcap</code>
          </Tip>
        </Phase>

        <Phase number={3} title="Simulation d'attaques et vulnérabilités PJSIP">
          <Warning>
            Ces tests sont <strong>strictement réservés à l'environnement de lab</strong>. Ne jamais exécuter ces commandes sur un réseau de production.
          </Warning>
          <CodeBlock code={`sudo apt install sipvicious -y

# Scan PJSIP (reconnaissance)
svmap 192.168.200.10

# Brute force sur le mot de passe
svwar 192.168.200.10 -e 1001 -w /usr/share/wordlists/rockyou.txt -u Pass1001

# Observer les tentatives échouées
tail -f /var/log/asterisk/security_log | grep 401`} />
          <InfoTable
            headers={["Vulnérabilité identifiée", "Impact"]}
            rows={[
              ["Identifiants SIP en clair", "Login/password visibles dans les en-têtes"],
              ["Audio RTP décodable", "Conversation interceptable et audible"],
              ["Brute force possible", "Pas de rate limiting par défaut"],
              ["Scan endpoints non protégé", "Liste des endpoints exposée"],
            ]}
          />
        </Phase>

        <Phase number={4} title="Sécurisation PJSIP : TLS / SRTP / ICE">
          <Steps items={[
            "Ajoutez le transport TLS dans pjsip.conf",
            "Modifiez les endpoints 1001 et 1002 : transport=transport-tls, ice_support=yes, media_encryption=sdes",
            "Redémarrez Asterisk et vérifiez le port TLS 5061",
          ]} />
          <CodeBlock code={`[transport-tls]
type=transport
protocol=tls
bind=0.0.0.0:5061
cert_file=/etc/asterisk/keys/asterisk.pem
priv_key_file=/etc/asterisk/keys/asterisk.key
method=tlsv1_2

; Modifier 1001 et 1002 :
[1001]
transport=transport-tls
ice_support=yes
media_encryption=sdes`} language="ini" />
          <CodeBlock code={`sudo systemctl restart asterisk
*CLI> pjsip show transports  # TLS doit apparaître sur le port 5061`} />
          <CodeBlock code={`# Règles iptables
sudo iptables -F
sudo iptables -A INPUT -p udp --dport 5060 -s 192.168.200.0/24 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 5060 -j DROP
sudo iptables -A INPUT -p tcp --dport 5061 -s 192.168.200.0/24 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5061 -j DROP
sudo iptables -A INPUT -p udp --dport 10000:20000 -s 192.168.200.0/24 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 10000:20000 -j DROP
sudo netfilter-persistent save`} />
          <InfoTable
            headers={["Critère", "UDP (non sécurisé)", "TLS/SRTP"]}
            rows={[
              ["Signalisation SIP", "En clair", "Chiffrée (TLS) ✔"],
              ["Audio RTP", "Décodable", "SRTP chiffré ✔"],
              ["Brute force", "Possible", "Bloqué (iptables) ✔"],
              ["Scan endpoints", "Visible", "Non accessible ✔"],
            ]}
          />
        </Phase>

        <Checklist items={[
          "pjsip show endpoints affiche 1001 et 1002",
          "Appel 1001 → 1002 fonctionnel (Zoiper)",
          "Capture Wireshark : trafic SRTP (non décodable après sécurisation)",
          "svmap timeout après activation des iptables",
        ]} />
      </TpSection>

      {/* TP 2 */}
      <TpSection number="Module 2" title="Déploiement et Sécurisation Docker PJSIP" duration="2h">
        <Phase number={1} title="Préparation de l'environnement Docker">
          <CodeBlock code={`mkdir -p ~/tp2-pjsip/{configs,keys,data} && cd ~/tp2-pjsip
cp /etc/asterisk/{pjsip.conf,extensions.conf} configs/
cp -r /etc/asterisk/keys configs/
sudo chown -R 1000:1000 configs keys data`} />
        </Phase>

        <Phase number={2} title="Fichier docker-compose.yml">
          <CodeBlock code={`version: '3.8'
services:
  asterisk-pjsip:
    image: ghcr.io/sipcapture/asterisk-pjsip:20-alpine
    container_name: ast-pjsip-tp2
    restart: always
    user: "asterisk:asterisk"
    ports:
      - "5060:5060/udp"
      - "5061:5061/tcp"
      - "10000-10100:10000-10100/udp"
    volumes:
      - ./configs/pjsip.conf:/etc/asterisk/pjsip.conf:ro
      - ./configs/extensions.conf:/etc/asterisk/extensions.conf:ro
      - ./keys:/etc/asterisk/keys:ro
      - ./data:/var/lib/asterisk
    networks:
      voip-vlan200:
        ipv4_address: 192.168.200.10
    cap_add:
      - NET_ADMIN
    sysctls:
      - net.ipv4.ip_forward=1

  pjsip-tester1:
    image: alpine:3.19
    command: >
      sh -c "apk add sipvicious asterisk-tools && svmap 192.168.200.10 && sleep infinity"
    networks:
      voip-vlan200:
        ipv4_address: 192.168.200.11

networks:
  voip-vlan200:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.200.0/24`} language="yaml" />
          <CodeBlock code={`docker compose up -d
docker compose logs -f asterisk-pjsip  # Vérifier le chargement PJSIP`} />
        </Phase>

        <Phase number={3} title="Test fonctionnel PJSIP Docker">
          <CodeBlock code={`docker exec -it asterisk-pjsip asterisk -r
*CLI> pjsip show endpoints
*CLI> core show version`} />
          <Steps items={[
            "Configurez Zoiper sur l'hôte → 192.168.200.10:5060",
            "Effectuez un appel 1001 → 1002",
            "Wireshark : filtre <code class='bg-gray-100 px-1 rounded text-xs'>udp.port==5060 or rtp</code>",
          ]} />
        </Phase>

        <Phase number={4} title="Simulation d'attaques + Sécurisation Docker PJSIP">
          <CodeBlock code={`# Attaques depuis le conteneur testeur
docker exec pjsip-tester1 svmap 192.168.200.10
docker exec pjsip-tester1 svwar 192.168.200.10 -e 1001

# Sécurisation TLS dans Docker
docker compose restart asterisk-pjsip

# Règles iptables dans le conteneur
docker exec asterisk-pjsip iptables -A INPUT -p udp -s 192.168.200.0/24 --dport 5060 -j ACCEPT
docker exec asterisk-pjsip iptables -A INPUT -p udp --dport 5060 -j DROP`} />
        </Phase>

        <Checklist items={[
          "docker compose up -d démarre sans erreur",
          "pjsip show endpoints affiche 1001 et 1002 dans le conteneur",
          "Appel fonctionnel depuis Zoiper",
          "svmap timeout après activation des iptables",
          "Wireshark : handshake TLS visible + flux SRTP chiffré",
        ]} />
      </TpSection>

      {/* TP 3 */}
      <TpSection number="Module 3" title="Supervision Zabbix / Grafana PJSIP" duration="2h">
        <Phase number={1} title="Installation Zabbix Server + Agent Docker">
          <CodeBlock code={`wget https://repo.zabbix.com/zabbix/6.4/ubuntu/pool/main/z/zabbix-release/zabbix-release_6.4-1+ubuntu22.04_all.deb
sudo dpkg -i zabbix-release_6.4-1+ubuntu22.04_all.deb
sudo apt update
sudo apt install zabbix-server-mysql zabbix-agent2 grafana -y`} />
          <Tip>Interface Zabbix : <strong>http://IP_ZABBIX/zabbix</strong> → Login : Admin / zabbix</Tip>
          <Steps items={[
            "Ajoutez le service zabbix-agent dans docker-compose.yml (ZBX_HOSTNAME: ast-pjsip-tp2, ZBX_SERVER_HOST: IP_ZABBIX)",
            "Dans Zabbix : Configuration > Hosts > Create host → Host name : ast-pjsip-tp2 | Agent IP : 192.168.200.10:10050",
          ]} />
        </Phase>

        <Phase number={2} title="Items et Triggers PJSIP (Tutoriel détaillé)">
          <p className="text-sm text-gray-600 mb-3">Configuration &gt; Hosts &gt; ast-pjsip-tp2 &gt; Items &gt; Create item</p>
          <InfoTable
            headers={["Nom de l'item", "Type", "Clé"]}
            rows={[
              ["PJSIP Endpoints Actifs", "Zabbix agent (exec)", `system.run["docker exec ast-pjsip pjsip show endpoints | grep -c Avail"]`],
              ["PJSIP TLS Port 5061", "Simple check", "net.tcp.service[tcp,192.168.200.10,5061]"],
              ["RTP Channels Actifs", "Zabbix agent (exec)", `system.run["docker exec ast-pjsip 'core show channels' | grep -c PJSIP"]`],
              ["CPU Docker Agent", "Zabbix agent", "system.cpu.util[,system,avg5]"],
              ["Registrations PJSIP", "Zabbix agent (exec)", `system.run["docker exec ast-pjsip 'pjsip show registrations' | grep -c Registered"]`],
            ]}
          />
          <Tip>
            Erreur "Permission denied" lors d'un system.run docker exec ? Ajoutez l'utilisateur zabbix au groupe docker :<br />
            <code>sudo usermod -aG docker zabbix && sudo systemctl restart zabbix-agent2</code>
          </Tip>
          <p className="text-sm font-medium text-gray-700 mt-3">Trigger « PJSIP Endpoints Dégradés »</p>
          <InfoTable
            headers={["Champ", "Valeur"]}
            rows={[
              ["Name", "PJSIP Endpoints Dégradés"],
              ["Severity", "WARNING (orange)"],
              ["Expression", "{ast-pjsip-tp2:system.run[...endpoints...].last()} < 2"],
              ["Recovery expression", "{ast-pjsip-tp2:system.run[...endpoints...].last()} >= 2"],
            ]}
          />
        </Phase>

        <Phase number={3} title="Dashboard Grafana PJSIP">
          <Steps items={[
            "Grafana : http://IP_ZABBIX:3000 → admin/admin",
            "Configuration > Datasources > Add > Zabbix : URL http://localhost/zabbix/, User: Admin",
            "Dashboards > New > ajouter les panels ci-dessous",
          ]} />
          <InfoTable
            headers={["Panel", "Type", "Query"]}
            rows={[
              ["PJSIP Endpoints", "Gauge", "system.run[endpoints]"],
              ["RTP Active + CPU", "Time Series", "RTP Channels + CPU"],
              ["TLS Status", "Stat (vert/rouge)", "net.tcp.service[5061]"],
              ["PJSIP Errors", "Logs", "Items log Zabbix"],
            ]}
          />
        </Phase>

        <Phase number={4} title="Simulation d'incidents + Plan HA">
          <CodeBlock code={`# Incident 1 : Stress CPU
docker run --rm -it --network tp2-pjsip_voip-vlan200 stress --cpu 4 --timeout 120s

# Incident 2 : Crash PJSIP
docker exec ast-pjsip asterisk -rx "module unload res_pjsip.so"

# Incident 3 : Blocage TLS
docker exec ast-pjsip iptables -I INPUT -p tcp --dport 5061 -j DROP`} />
          <CodeBlock code={`# Plan de haute disponibilité — Sauvegarde
docker compose down
tar czf ast-backup-$(date +%Y%m%d).tar.gz data configs/

# Restauration
docker compose up -d`} />
        </Phase>

        <Checklist items={[
          "L'item 'PJSIP Endpoints Actifs' remonte 2 dans Zabbix",
          "Le trigger WARNING s'active quand un Zoiper se déconnecte",
          "Le dashboard Grafana affiche tous les panels en temps réel",
          "L'alerte CPU > 80 % se déclenche lors du stress test",
        ]} />
      </TpSection>

      {/* TP 4 */}
      <TpSection number="Module 4" title="Diagnostic QoS Mobile PJSIP" duration="2h">
        <Phase number={1} title="Endpoint mobile PJSIP">
          <CodeBlock code={`; Transport WebRTC optionnel (WebSocket Secure)
[transport-wss]
type=transport
protocol=wss
bind=0.0.0.0:8089

; Endpoint mobile optimisé
[1002-mobile]
type=endpoint
transport=transport-udp
context=mobile-qos
allow=opus,g722         ; Opus 6-32 kbps — adapté 4G
auth=auth-1002
aors=aors-1002
direct_media=no
force_rport=yes
rtp_symmetric=yes
ice_support=yes         ; Obligatoire NAT 4G
dtls_enable=yes
rtcp_mux=yes            ; Économie de bande passante
media_encryption=sdes
tos_audio=184           ; DSCP EF (Expedited Forwarding)
max_audio_streams=1     ; Limite la consommation batterie`} language="ini" />
        </Phase>

        <Phase number={2} title="Mesures QoS Wireshark">
          <Steps items={[
            "Lancez un appel Zoiper mobile → endpoint 1002-mobile",
            "Dans Wireshark : Statistics > RTP > Stream",
            "Vérifiez : Jitter moyen < 20 ms | Packet Loss < 0,5 % | MOS estimé > 4,0",
          ]} />
        </Phase>

        <Phase number={3} title="Configuration Traffic Control (TC) pour prioriser RTP">
          <CodeBlock code={`# Hiérarchie HTB
sudo tc qdisc add dev docker0 root handle 1: htb default 30

# Classe haute priorité pour RTP
sudo tc class add dev docker0 parent 1: classid 1:10 htb rate 20mbit ceil 50mbit prio 1
sudo tc qdisc add dev docker0 parent 1:10 pfifo limit 1000

# Associer DSCP EF (valeur 46) à la classe RTP
sudo tc filter add dev docker0 protocol ip prio 1 u32 match ip dscp 46 0xff flowid 1:10`} />
        </Phase>

        <Phase number={4} title="Résultats et recommandations QoS">
          <InfoTable
            headers={["Scénario", "Latence", "Jitter", "Loss", "MOS"]}
            rows={[
              ["Sans QoS", "180 ms", "65 ms", "3,2 %", "2,8"],
              ["Avec Opus", "95 ms", "22 ms", "0,8 %", "4,1"],
              ["+ DSCP + TC HTB", "42 ms", "12 ms", "0,1 %", "4,4"],
            ]}
          />
          <Tip>
            Recommandations : <strong>ice_support=yes</strong> est obligatoire en NAT 4G | <strong>rtcp_mux=yes</strong> réduit la bande passante | <strong>media_encryption=dtls</strong> automatise la négociation SRTP.
          </Tip>
        </Phase>

        <div className="border-t border-gray-100 pt-5">
          <h3 className="font-semibold text-gray-800 mb-3">Commandes de diagnostic rapide</h3>
          <CodeBlock code={`*CLI> pjsip show contacts       # Liste des enregistrements actifs
*CLI> pjsip notify endpoint 1001 # Test push vers 1001
*CLI> core set verbose 5         # Activer les logs détaillés
*CLI> rtp set debug on           # Activer le debug RTP
*CLI> pjsip show registrations   # État des registrations`} />
        </div>

        <Checklist items={[
          "Endpoint mobile 1002-mobile charge correctement (pjsip show endpoints)",
          "MOS estimé ≥ 4,0 dans Wireshark Statistics > RTP",
          "Jitter < 20 ms avec configuration TC HTB",
          "Le monitoring Grafana (TP3) trace le MOS en temps réel",
        ]} />
      </TpSection>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Déblocage rapide (si ça ne marche pas)</h2>
        <ul className="space-y-2 text-sm text-gray-700 mb-4">
          <li>1. Vérifier que le service Asterisk tourne : <span className="font-mono">systemctl status asterisk</span></li>
          <li>2. Vérifier les enregistrements SIP : <span className="font-mono">pjsip show endpoints</span> puis <span className="font-mono">pjsip show contacts</span></li>
          <li>3. Vérifier les ports exposés : <span className="font-mono">ss -luntp | grep -E &quot;5060|5061|10000&quot;</span></li>
          <li>4. Vérifier la résolution DNS/NAT côté clients avant de changer la conf PJSIP</li>
          <li>5. Si audio one-way, revérifier NAT, ICE et plage RTP autorisée dans le pare-feu</li>
        </ul>
        <CodeBlock code={`# Logs en direct
sudo journalctl -u asterisk -f

# Tests utiles dans la console Asterisk
asterisk -rvvv
pjsip show registrations
rtp set debug on`} />
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Annexes et ressources en ligne</h2>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>
            <a className="text-indigo-600 hover:underline" href="https://docs.asterisk.org/Getting-Started/" target="_blank" rel="noreferrer">
              Asterisk Docs - Getting Started
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/PJSIP-Configuration-Sections-and-Relationships/" target="_blank" rel="noreferrer">
              Asterisk Docs - PJSIP Configuration Sections and Relationships
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://www.zabbix.com/documentation/current/en/manual" target="_blank" rel="noreferrer">
              Zabbix - Official Documentation
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://grafana.com/docs/grafana/latest/" target="_blank" rel="noreferrer">
              Grafana - Official Documentation
            </a>
          </li>
        </ul>
      </div>
    </WikiLayout>
  );
}
