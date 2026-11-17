import {
  WikiLayout, TpSection, Phase, Steps, CodeBlock, Tip, Warning, Checklist, InfoTable,
} from "../components";

export const metadata = {
  title: "Guide LoRaWAN — ChirpStack · MQTT · Node-RED",
  robots: { index: false, follow: false },
};

export default function LoRaWANPage() {
  return (
    <WikiLayout
      title="LoRaWAN — ChirpStack · MQTT · Node-RED"
      subtitle="Modules 0 à 4 · Déploiement, intégration et sécurisation"
      description="Déploiement de capteurs LoRaWAN sur Raspberry Pi avec ChirpStack, Mosquitto et Node-RED. Même infrastructure pour tous les sujets — seuls les capteurs et topics MQTT changent."
      color="from-emerald-600 to-teal-700"
    >

      {/* TP 0 */}
      <TpSection number="Module 0" title="Installation de ChirpStack sur Raspberry Pi" duration="1h30">
        <Tip>
          Cette étape n'est faite <strong>qu'une seule fois</strong> avant les modules 1 à 4. Si l'infrastructure est déjà installée, parcourez ce module pour comprendre l'architecture.
        </Tip>

        <Phase number={1} title="Préparation du Raspberry Pi">
          <Steps items={[
            "Connectez-vous en SSH : <code class='bg-gray-100 px-1 rounded text-xs'>ssh pi@&lt;IP_raspberry&gt;</code> (mdp : raspberry)",
            "Mettez à jour le système avant toute installation.",
          ]} />
          <CodeBlock code={`sudo apt update && sudo apt upgrade -y
# Cette étape peut prendre 5 à 10 minutes`} />
        </Phase>

        <Phase number={2} title="Installation des dépendances (Mosquitto, Redis, PostgreSQL)">
          <CodeBlock code={`sudo apt install -y \\
  mosquitto mosquitto-clients \\
  redis-server redis-tools \\
  postgresql

# Vérification des services
sudo systemctl status mosquitto   # Active: active (running)
sudo systemctl status redis
sudo systemctl status postgresql`} />
        </Phase>

        <Phase number={3} title="Configuration de PostgreSQL pour ChirpStack">
          <CodeBlock code={`sudo -u postgres psql

-- Dans le prompt psql :
CREATE ROLE chirpstack WITH LOGIN PASSWORD 'chirpstack';
CREATE DATABASE chirpstack WITH OWNER chirpstack;
\\c chirpstack
CREATE EXTENSION pg_trgm;
\\q`} />
          <Warning>
            En production, utilisez un mot de passe fort et mettez-le à jour dans <code>/etc/chirpstack/chirpstack.toml</code> (clé <code>postgresql.dsn</code>).
          </Warning>
        </Phase>

        <Phase number={4} title="Ajout du dépôt ChirpStack et installation">
          <CodeBlock code={`sudo apt install -y gpg
sudo mkdir -p /etc/apt/keyrings/
sudo sh -c 'wget -q -O - https://artifacts.chirpstack.io/packages/chirpstack.key | gpg --dearmor > /etc/apt/keyrings/chirpstack.gpg'
echo "deb [signed-by=/etc/apt/keyrings/chirpstack.gpg] https://artifacts.chirpstack.io/packages/4.x/deb stable main" | sudo tee /etc/apt/sources.list.d/chirpstack.list
sudo apt update
sudo apt install -y chirpstack-gateway-bridge chirpstack`} />
        </Phase>

        <Phase number={5} title="Configuration du Gateway Bridge (région EU868)">
          <Steps items={[
            "Ouvrez le fichier : <code class='bg-gray-100 px-1 rounded text-xs'>sudo nano /etc/chirpstack-gateway-bridge/chirpstack-gateway-bridge.toml</code>",
            "Localisez la section <code>[integration.mqtt]</code> et adaptez les templates.",
          ]} />
          <CodeBlock code={`[integration.mqtt]
event_topic_template   = "eu868/gateway/{{ .GatewayID }}/event/{{ .EventType }}"
command_topic_template = "eu868/gateway/{{ .GatewayID }}/command/#"`} language="toml" />
          <CodeBlock code={`sudo systemctl start chirpstack-gateway-bridge
sudo systemctl enable chirpstack-gateway-bridge
sudo systemctl status chirpstack-gateway-bridge  # doit être Active`} />
        </Phase>

        <Phase number={6} title="Démarrage de ChirpStack et accès navigateur">
          <CodeBlock code={`sudo systemctl start chirpstack
sudo systemctl enable chirpstack
sudo journalctl -f -n 100 -u chirpstack`} />
          <InfoTable
            headers={["Accès", "URL"]}
            rows={[
              ["Depuis le Raspberry Pi", "http://localhost:8080"],
              ["Depuis un PC du réseau", "http://<IP_raspberry>:8080"],
            ]}
          />
          <Tip>
            Identifiants par défaut : <strong>admin / admin</strong> — Changez immédiatement le mot de passe après la première connexion.
          </Tip>
        </Phase>

        <Phase number={7} title="Installation de Node-RED">
          <CodeBlock code={`bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
# Répondez 'y' aux questions — peut prendre 5 à 10 minutes

sudo systemctl enable nodered.service
sudo systemctl start nodered.service

# Installer le module Dashboard
cd ~/.node-red
npm install node-red-dashboard
sudo systemctl restart nodered.service`} />
          <InfoTable
            headers={["Interface", "URL"]}
            rows={[
              ["Éditeur de flows", "http://localhost:1880"],
              ["Dashboard (interface)", "http://localhost:1880/ui"],
              ["Depuis un autre PC", "http://<IP_raspberry>:1880"],
            ]}
          />
        </Phase>

        <Checklist items={[
          "http://localhost:8080 affiche l'interface ChirpStack — connexion admin/admin réussie",
          "http://localhost:1880 affiche l'éditeur Node-RED",
          "sudo systemctl status chirpstack → Active: active (running)",
          "sudo systemctl status mosquitto → Active: active (running)",
          "sudo systemctl status nodered → Active: active (running)",
          "Le mot de passe admin a été changé",
        ]} />
      </TpSection>

      {/* TP 1 */}
      <TpSection number="Module 1" title="Passerelle LoRaWAN et premier capteur dans ChirpStack" duration="2h">
        <Phase number={1} title="Enregistrement de la passerelle Laird RG186">
          <Steps items={[
            "Identifiez l'adresse IP de la passerelle avec <code class='bg-gray-100 px-1 rounded text-xs'>nmap -sn 192.168.1.0/24</code>",
            "Ouvrez l'interface web de la RG186 et notez le Gateway EUI (16 caractères hexa).",
            "Vérifiez que le Packet Forwarder pointe vers l'IP du Raspberry Pi, port UDP <strong>1700</strong>.",
          ]} />
          <Steps items={[
            "Dans ChirpStack → <em>Gateways</em> → <em>+ Add gateway</em>",
            "Renseignez : Name = Gateway-RG186-Labo | Gateway EUI = (valeur relevée)",
            "Cliquez Submit et vérifiez le statut <strong>Online</strong> (point vert, peut prendre 1-2 min).",
          ]} />
          <Warning>
            La gateway reste 'Never Seen' ? Vérifiez que le Packet Forwarder pointe bien vers l'IP du Raspberry Pi port UDP 1700, et que le service chirpstack-gateway-bridge est démarré.
          </Warning>
        </Phase>

        <Phase number={2} title="Création du Device Profile pour le RS1xx">
          <InfoTable
            headers={["Paramètre", "Valeur"]}
            rows={[
              ["Name", "RS1xx-Temp-Humidity-EU868"],
              ["Region", "EU868"],
              ["MAC version", "LoRaWAN 1.0.3"],
              ["Regional parameters revision", "RP002-1.0.3"],
              ["Supports OTAA", "✅ Oui"],
              ["Supports Class B / C", "❌ Non — Classe A uniquement"],
            ]}
          />
          <Tip>
            Convention de nommage : <code>&lt;Fabricant&gt;-&lt;Modèle&gt;-&lt;Région&gt;</code> — ex. <em>RS1xx-Temp-Humidity-EU868</em>, <em>Dragino-SE01LB-EU868</em>
          </Tip>
        </Phase>

        <Phase number={3} title="Création de l'Application et enregistrement du capteur RS1xx">
          <Steps items={[
            "Applications → + Add application → Name : <strong>Supervision-Chaine-Froid</strong>",
            "Dans l'application → Devices → + Add device → renseignez le DevEUI (étiquette du capteur)",
            "Sélectionnez le Device Profile <em>RS1xx-Temp-Humidity-EU868</em>",
            "Dans l'onglet OTAA Keys, entrez l'AppKey (application mobile Laird Sentrius)",
            "Déclenchez le join sur le capteur (bouton physique) et vérifiez les frames : Join Request → Join Accept → Uplinks",
          ]} />
          <InfoTable
            headers={["Identifiant", "Description", "Où le trouver"]}
            rows={[
              ["DevEUI", "Identifiant unique 64-bit", "Étiquette au dos du capteur"],
              ["AppEUI / JoinEUI", "Identifiant 64-bit", "Application mobile Laird Sentrius"],
              ["AppKey", "Clé de chiffrement 128-bit OTAA", "Application mobile Laird Sentrius"],
            ]}
          />
        </Phase>

        <Checklist items={[
          "La gateway RG186 affiche le statut Online dans ChirpStack",
          "Le Device Profile RS1xx-EU868 est créé",
          "L'Application 'Supervision-Chaine-Froid' est créée",
          "Le capteur RS1xx envoie des uplinks visibles dans ChirpStack",
          "Les valeurs de température et humidité sont lisibles dans l'onglet 'Device data'",
        ]} />
      </TpSection>

      {/* TP 2 */}
      <TpSection number="Module 2" title="Intégration MQTT et tableau de bord Node-RED" duration="2h">
        <Phase number={1} title="Configuration de Mosquitto avec authentification">
          <CodeBlock code={`# Créer les utilisateurs MQTT
sudo mosquitto_passwd -c /etc/mosquitto/passwd chirpstack_user
sudo mosquitto_passwd /etc/mosquitto/passwd nodered_user

# Fichier de configuration
sudo nano /etc/mosquitto/conf.d/campus-lasalle.conf`} />
          <CodeBlock code={`listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd`} language="conf" />
          <CodeBlock code={`sudo systemctl restart mosquitto

# Test : abonnez-vous dans un terminal
mosquitto_sub -h localhost -p 1883 -u nodered_user -P <votre_mdp> -t test/#

# Dans un autre terminal, publiez
mosquitto_pub -h localhost -p 1883 -u nodered_user -P <votre_mdp> -t test/hello -m 'Mosquitto OK'`} />
        </Phase>

        <Phase number={2} title="Liaison ChirpStack → MQTT">
          <Steps items={[
            "Dans ChirpStack, ouvrez l'Application → Integrations → + Add integration → MQTT",
          ]} />
          <InfoTable
            headers={["Paramètre", "Valeur"]}
            rows={[
              ["Event topic template", "froid/rs1xx/{{.DeviceName}}/uplink"],
              ["MQTT broker", "tcp://localhost:1883"],
              ["Username", "chirpstack_user"],
            ]}
          />
          <Tip>
            Convention des topics par projet : <strong>froid/</strong>, <strong>agri/</strong>, <strong>qai/</strong>, <strong>occupation/</strong> — le wildcard <code>+</code> s'abonne à tous les capteurs d'un projet.
          </Tip>
        </Phase>

        <Phase number={3} title="Création du flow Node-RED — Dashboard temps réel">
          <InfoTable
            headers={["Nœud", "Configuration"]}
            rows={[
              ["mqtt in", "Server: localhost:1883 | Topic: froid/rs1xx/+/uplink | Output: JSON"],
              ["json", "Parse la chaîne JSON"],
              ["function", "Extrait température et humidité — 2 sorties"],
              ["ui_gauge x2", "Température (-10→50 °C) | Humidité (0→100 %HR)"],
              ["ui_chart", "Graphique de tendance — 60 dernières valeurs"],
              ["debug", "Affiche le payload complet"],
            ]}
          />
          <CodeBlock code={`// Nœud function : 'Extraire Temp & Humidité' (configurer 2 outputs)
var payload = msg.payload;
var temperature = payload.object.temperature;
var humidity    = payload.object.humidity;

var msg1 = { payload: temperature, topic: 'temperature' };
var msg2 = { payload: humidity,    topic: 'humidity' };
return [msg1, msg2];`} language="javascript" />
          <Steps items={[
            "Glissez-déposez les nœuds depuis la palette gauche",
            "Reliez : mqtt in → json → function → [ui_gauge, ui_gauge, ui_chart, debug]",
            "Cliquez <strong>Deploy</strong> (bouton rouge en haut à droite)",
            "Accédez au Dashboard : <code>http://localhost:1880/ui</code>",
          ]} />
        </Phase>

        <Checklist items={[
          "MQTT Explorer reçoit les messages JSON sur froid/rs1xx/+/uplink",
          "Le flow Node-RED ne présente aucun nœud rouge (erreur)",
          "Le Dashboard http://localhost:1880/ui affiche les valeurs de température et humidité",
          "Le graphique de tendance trace l'évolution dans le temps",
        ]} />
      </TpSection>

      {/* TP 3 */}
      <TpSection number="Module 3" title="Sécurisation MQTT (TLS) et système d'alertes" duration="2h">
        <Phase number={1} title="Activation du chiffrement TLS sur Mosquitto">
          <Steps items={[
            "Créez le répertoire de travail pour les certificats : <code class='bg-gray-100 px-1 rounded text-xs'>mkdir -p ~/mqtt-certs && cd ~/mqtt-certs</code>",
            "Générez la clé CA et le certificat CA",
            "Générez la clé et le certificat serveur",
            "Copiez les certificats dans /etc/mosquitto/certs/",
          ]} />
          <CodeBlock code={`# Génération du CA
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \\
  -subj "/C=FR/ST=IDF/L=Issy/O=CampusLaSalle/CN=MQTTRootCA"

# Certificat serveur
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \\
  -subj "/C=FR/ST=IDF/L=Issy/O=CampusLaSalle/CN=$(hostname -I | awk '{print $1}')"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \\
  -CAcreateserial -out server.crt -days 3650

# Copie des certificats
sudo mkdir -p /etc/mosquitto/certs
sudo cp ca.crt server.crt server.key /etc/mosquitto/certs/
sudo chown mosquitto:mosquitto /etc/mosquitto/certs/*
sudo chmod 640 /etc/mosquitto/certs/*`} />
          <CodeBlock code={`# Contenu de /etc/mosquitto/conf.d/campus-lasalle.conf
listener 1883 127.0.0.1
allow_anonymous false
password_file /etc/mosquitto/passwd

listener 8883
allow_anonymous false
password_file /etc/mosquitto/passwd
cafile   /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile  /etc/mosquitto/certs/server.key
tls_version tlsv1.2`} language="conf" />
          <CodeBlock code={`sudo systemctl restart mosquitto

# Test TLS
mosquitto_pub -h localhost -p 8883 --cafile ~/mqtt-certs/ca.crt \\
  -u nodered_user -P <votre_mdp> -t test/tls -m 'TLS OK'`} />
        </Phase>

        <Phase number={2} title="Mise à jour de ChirpStack et Node-RED pour TLS">
          <Steps items={[
            "Affichez le CA : <code class='bg-gray-100 px-1 rounded text-xs'>cat ~/mqtt-certs/ca.crt</code> et copiez son contenu",
            "Dans ChirpStack → Application → Integrations → MQTT : changez <code>tcp://localhost:1883</code> en <code>ssl://localhost:8883</code>",
            "Collez le contenu de ca.crt dans le champ <em>CA certificate</em>",
            "Dans Node-RED → nœud mqtt in → Port : 8883 → Enable secure (SSL/TLS) → chemin /etc/node-red/ca.crt",
            "Redéployez le flow et vérifiez que le nœud affiche 'connected'",
          ]} />
        </Phase>

        <Phase number={3} title="Système d'alertes par seuils (chaîne du froid)">
          <Steps items={[
            "Ajoutez un nœud <strong>switch</strong> après l'extraction de température",
            "Rule 1 : > 8 → output 1 (alerte haute) | Rule 2 : < 2 → output 2 (alerte basse)",
            "Sur les outputs 1 et 2, ajoutez un nœud <strong>function</strong> 'Créer message alerte'",
          ]} />
          <CodeBlock code={`// Nœud function : 'Préparer alerte température'
var alerte = {
  type: 'TEMPERATURE_HORS_PLAGE',
  valeur: msg.payload,
  seuil_min: 2, seuil_max: 8, unite: '°C',
  horodatage: new Date().toLocaleString('fr-FR'),
  message: 'ALERTE : Température ' + msg.payload + ' °C hors plage [2–8 °C]'
};
msg.payload = alerte;
msg.topic   = 'ALERTE CHAÎNE DU FROID';
return msg;`} language="javascript" />
          <Tip>
            Pour éviter le spam, ajoutez un nœud <strong>delay</strong> en mode <em>Rate limit</em> : 1 message par 5 minutes. Pour tester sans attendre, utilisez un nœud <strong>inject</strong> avec payload = 10.
          </Tip>
        </Phase>

        <Checklist items={[
          "Mosquitto accepte les connexions TLS sur le port 8883",
          "ChirpStack et Node-RED communiquent via ssl://localhost:8883",
          "Le nœud switch détecte les dépassements de seuils",
          "Une notification rouge apparaît dans le Dashboard en cas d'alerte",
          "Un log est envoyé lors du test d'injection d'une valeur hors seuil",
        ]} />
      </TpSection>

      {/* TP 4 */}
      <TpSection number="Module 4" title="Infrastructure multi-projets et capteurs spécialisés" duration="2h">
        <Phase number={1} title="Règles d'isolation multi-projets">
          <InfoTable
            headers={["Composant", "Règle d'isolation"]}
            rows={[
              ["Application ChirpStack", "Une application par sujet — jamais plusieurs capteurs hétérogènes"],
              ["Device Profile", "Un profil par modèle — réutilisable sur plusieurs Applications"],
              ["Topics MQTT", "Préfixe distinct : froid/, agri/, qai/, occupation/"],
              ["Onglet Node-RED", "Un Tab par projet (double-clic sur fond vide → Add tab)"],
            ]}
          />
        </Phase>

        <Phase number={2} title="Sujet 2 — Capteur sol Dragino SE01-LB">
          <Steps items={[
            "Créez l'Application 'Supervision-Sol-Agriculture' dans ChirpStack",
            "Créez le Device Profile 'Dragino-SE01LB-EU868'",
            "Dans l'onglet Codec du Device Profile, collez le décodeur JavaScript ci-dessous",
            "Topic MQTT : <code>agri/sol/{{.DeviceName}}/uplink</code>",
            "Dans Node-RED : nouvel onglet 'Agriculture Sol', variables : soil_moisture, soil_temperature, ec",
          ]} />
          <CodeBlock code={`// Codec Dragino SE01-LB — Device Profile → Codec
function decodeUplink(input) {
  var b = input.bytes;
  var bat      = ((b[0] << 8) | b[1]) / 1000.0;        // Tension batterie (V)
  var moisture = ((b[2] << 8) | b[3]) / 100.0;         // Humidité volumétrique (%VWC)
  var raw_temp = (b[4] << 8) | b[5];
  var temp     = (raw_temp > 32767 ? raw_temp - 65536 : raw_temp) / 10.0;  // °C
  var ec       = (b[6] << 8) | b[7];                   // Conductivité (µS/cm)
  return {
    data: { battery_v: bat, soil_moisture: moisture, soil_temperature: temp, ec: ec }
  };
}`} language="javascript" />
        </Phase>

        <Phase number={3} title="Sujet 3 — Indicateur CO₂ coloré (3 niveaux)">
          <CodeBlock code={`// Nœud function : 'Niveau Qualité Air'
var co2 = msg.payload;
var niveau, couleur, emoji;
if (co2 < 800)       { niveau = 'BON';    couleur = '#00A36C'; emoji = '🟢'; }
else if (co2 < 1200) { niveau = 'MOYEN';  couleur = '#FFA500'; emoji = '🟠'; }
else                 { niveau = 'MAUVAIS';couleur = '#C00000'; emoji = '🔴'; }
msg.payload = co2;
msg.color   = couleur;
msg.niveau  = emoji + ' ' + niveau + ' — ' + co2 + ' ppm CO₂';
return msg;`} language="javascript" />
          <Tip>
            Seuils : vert &lt; 800 ppm | orange &lt; 1200 ppm | rouge ≥ 1200 ppm. Connectez la sortie à un nœud <strong>ui_text</strong> pour afficher <code>msg.niveau</code> dans le Dashboard.
          </Tip>
        </Phase>

        <Phase number={4} title="Sujet 4 — Présence PIR et gestion horaire">
          <CodeBlock code={`// Nœud function : 'État Occupation'
var pir = msg.payload.object.pir;          // true = présence
var lux = msg.payload.object.illuminance;  // lux
msg.presence = pir;
msg.lux      = lux;
msg.payload  = pir ? 1 : 0;
msg.etat     = pir ? '🔴 OCCUPÉE' : '🟢 LIBRE';
msg.eclairage_inutile = (!pir && lux > 500);
return msg;

// Alerte hors horaires (nœud function suivant)
var heure    = new Date().getHours();
var presence = msg.presence;
if (presence && (heure >= 22 || heure < 7)) {
  msg.payload = '⚠️ ALERTE : Présence hors horaires détectée à ' + heure + 'h';
  return msg;
}
if (msg.eclairage_inutile) {
  msg.payload = '💡 ALERTE : Éclairage actif sans présence (lux=' + msg.lux + ')';
  return msg;
}
return null;`} language="javascript" />
        </Phase>

        <Checklist items={[
          "L'Application 'Supervision-Sol-Agriculture' coexiste avec 'Supervision-Chaine-Froid' sans conflit",
          "Les topics MQTT sont distincts (froid/, agri/, qai/, occupation/)",
          "Le codec Dragino SE01-LB décode humidité, température et conductivité",
          "L'indicateur CO₂ change de couleur selon les 3 seuils",
          "L'alerte de présence hors horaires se déclenche correctement",
        ]} />

        {/* Checklist globale */}
        <div className="border-t border-gray-100 pt-5">
          <h3 className="font-semibold text-gray-800 mb-3">Checklist globale — Validation opérationnelle</h3>
          <InfoTable
            headers={["URL / Port", "Service"]}
            rows={[
              ["http://localhost:8080", "ChirpStack — Interface d'administration (admin/admin)"],
              ["http://localhost:1880", "Node-RED — Éditeur de flows"],
              ["http://localhost:1880/ui", "Node-RED Dashboard — Visualisation"],
              ["localhost:1883", "MQTT Mosquitto — Port non chiffré (local)"],
              ["localhost:8883", "MQTT Mosquitto — Port TLS"],
            ]}
          />
          <div className="mt-4 bg-indigo-50 border border-indigo-200 rounded-xl p-4 space-y-2">
            <p className="text-sm font-semibold text-indigo-800 mb-2">💡 Conseils pour le jour de l'épreuve</p>
            {[
              "Lisez entièrement la fiche sujet avant de commencer.",
              "Notez en priorité : DevEUI, AppEUI, AppKey du capteur.",
              "Créez toujours : Device Profile → Application → Device.",
              "Vérifiez les uplinks dans ChirpStack AVANT de passer à MQTT/Node-RED.",
              "Prenez des captures d'écran régulièrement — c'est votre livrable principal.",
              "En cas de blocage : capteur → RG186 → gateway-bridge → ChirpStack → MQTT → Node-RED.",
            ].map((tip, i) => (
              <p key={i} className="text-sm text-indigo-700 flex gap-2"><span className="font-bold">{i + 1}.</span>{tip}</p>
            ))}
          </div>
        </div>
      </TpSection>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Déblocage rapide (si ça ne marche pas)</h2>
        <ul className="space-y-2 text-sm text-gray-700 mb-4">
          <li>1. Vérifier les services clés : ChirpStack, PostgreSQL, Redis, Mosquitto</li>
          <li>2. Vérifier l'arrivée des uplinks dans ChirpStack avant Node-RED</li>
          <li>3. Vérifier la gateway et la région radio (EU868, US915, etc.)</li>
          <li>4. Vérifier DevEUI/AppEUI/AppKey et Device Profile</li>
          <li>5. Vérifier le topic MQTT exact utilisé dans Node-RED</li>
        </ul>
        <CodeBlock code={`# État des services
sudo systemctl status chirpstack mosquitto redis-server postgresql

# Test MQTT local
mosquitto_sub -h localhost -t "#" -v

# Logs ChirpStack
sudo journalctl -u chirpstack -f`} />
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="font-bold text-gray-900 mb-4">Annexes et ressources en ligne</h2>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>
            <a className="text-indigo-600 hover:underline" href="https://www.chirpstack.io/docs/" target="_blank" rel="noreferrer">
              ChirpStack - Documentation officielle
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://nodered.org/docs/" target="_blank" rel="noreferrer">
              Node-RED - Documentation officielle
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://mosquitto.org/documentation/" target="_blank" rel="noreferrer">
              Eclipse Mosquitto - Documentation officielle
            </a>
          </li>
          <li>
            <a className="text-indigo-600 hover:underline" href="https://lora-alliance.org/resource_hub/lorawan-specification-v1-0-3/" target="_blank" rel="noreferrer">
              LoRa Alliance - LoRaWAN Specification
            </a>
          </li>
        </ul>
      </div>
    </WikiLayout>
  );
}
