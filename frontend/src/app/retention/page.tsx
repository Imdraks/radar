import Link from "next/link";
import legal from "@/config/legal.json";
import {
  LegalDocument,
  LegalSection,
  ContractLink,
} from "@/components/legal/LegalDocument";
export default function Page() {
  return (
    <LegalDocument title="Conservation et fin de traitement">
      <LegalSection title="Durées déclarées">
        <p>
          Contact commercial :{" "}
          {legal.contactRetention ||
            "durée à définir avant ouverture commerciale"}
          . Journaux de sécurité :{" "}
          {legal.securityLogsRetention ||
            "durée à définir avant ouverture commerciale"}
          . Données actives de workspace :{" "}
          {legal.workspaceRetention ||
            "durée à définir avant ouverture commerciale"}
          . Dossiers de droits :{" "}
          {legal.rightsRequestRetention ||
            "durée à définir avant ouverture commerciale"}
          .
        </p>
        <p>
          Ces catégories ne partagent pas une durée universelle. Le contrat, la
          finalité, l’obligation légale et la nécessité de preuve doivent être
          distingués. Une donnée comptable soumise à conservation n’autorise pas
          à garder toutes les données du compte pendant la même durée.
        </p>
      </LegalSection>
      <LegalSection title="Politique applicable">
        <p>
          <ContractLink
            url={legal.retentionPolicyUrl}
            label="Politique de production approuvée"
          />
          . Les{" "}
          <Link className="underline" href="/contracts">
            versions contractuelles publiées
          </Link>{" "}
          conservent les textes effectivement proposés. La publication d’un
          texte ne déclenche pas une purge automatique.
        </p>
      </LegalSection>
      <LegalSection title="Contrôle et traitement des demandes">
        <p>
          L’administrateur peut télécharger les données métier et consulter un
          inventaire depuis{" "}
          <Link className="underline" href="/settings/privacy">
            Données et droits
          </Link>
          . Cet inventaire ne constitue pas une décision d’effacement. Une
          demande est examinée en tenant compte des factures, contrats, autres
          membres, litiges et sauvegardes, puis la réponse est tracée.
        </p>
      </LegalSection>
    </LegalDocument>
  );
}
