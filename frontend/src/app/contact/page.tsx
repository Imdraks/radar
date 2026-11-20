'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, ArrowUpRight, Check, Send } from 'lucide-react';
import { RadarSpinner } from '@/components/ui/radar-loader';
import { Button } from '@/components/ui/button';
import { ForceLightMode } from '@/components/landing/ForceLightMode';
import { ContactNavigation } from '@/components/landing/ContactNavigation';
import { submitContactMessage } from '@/lib/contact';
import './contact.css';

const PLANS = [
  { value: '', label: 'Je souhaite être conseillé' },
  { value: 'core', label: 'Radar Core' },
  { value: 'premium', label: 'Radar Premium' },
  { value: 'business', label: 'Radar Business' },
  { value: 'custom', label: 'Radar Addons — besoin sur mesure' },
];
const STEPS = ['Votre nom', 'Votre e-mail', 'Votre agence', 'Votre offre', 'Votre message', 'Récapitulatif'];
const COPY = [
  { kicker: 'Pour commencer', title: 'Commençons par', accent: 'votre nom.', description: 'Derrière chaque beau projet, il y a une rencontre.' },
  { kicker: 'Restons en contact', title: 'Où pouvons-nous', accent: 'vous répondre ?', description: 'Votre adresse professionnelle, pour poursuivre la conversation.' },
  { kicker: 'Un peu de contexte', title: 'Parlons de', accent: 'votre agence.', description: 'Ces informations sont facultatives. Vous pouvez passer cette étape.' },
  { kicker: 'Le bon point de départ', title: 'Radar, à', accent: 'votre mesure.', description: 'Une offre en tête ? Sinon, nous pouvons vous aider à choisir.' },
  { kicker: 'À vous de jouer', title: 'Qu’avez-vous', accent: 'en tête ?', description: 'Votre organisation, une question, un besoin précis. On vous écoute.' },
  { kicker: 'Un dernier regard', title: 'Tout est prêt', accent: 'pour échanger.', description: 'Vérifiez votre demande avant de nous la transmettre.' },
];
const EMPTY = { name: '', email: '', company: '', phone: '', plan: '', message: '' };

export default function ContactPage() {
  const [form, setForm] = useState(EMPTY);
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState<'forward' | 'back'>('forward');
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [fieldError, setFieldError] = useState('');
  const panel = useRef<HTMLDivElement>(null);
  const mounted = useRef(false);
  const sending = useRef(false);
  const isSuccess = status === 'success';

  useEffect(() => {
    setReady(true);
    const params = new URLSearchParams(window.location.search);
    const plan = params.get('plan') || '';
    if (params.get('offer') === 'mcp') {
      setForm(previous => ({ ...previous, plan: 'custom', message: 'Je souhaite connaître les conditions et l’activation du connecteur ChatGPT / MCP pour mon workspace Radar.' }));
    } else if (PLANS.some(option => option.value === plan)) {
      setForm(previous => ({ ...previous, plan }));
    }
  }, []);

  useEffect(() => {
    if (!mounted.current) { mounted.current = true; return; }
    (panel.current?.querySelector<HTMLElement>('input, select, textarea') ?? panel.current?.querySelector<HTMLElement>('h2'))?.focus();
  }, [step, isSuccess]);

  const update = (key: keyof typeof EMPTY, value: string) => {
    setForm(previous => ({ ...previous, [key]: value }));
    setFieldError('');
  };
  const move = (next: number) => {
    setDirection(next < step ? 'back' : 'forward');
    setFieldError('');
    setStep(next);
  };
  const invalidStep = () => {
    if (form.name.trim().length < 2) return 0;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) return 1;
    if (form.company.length > 200 || form.phone.length > 40) return 2;
    if (!PLANS.some(option => option.value === form.plan)) return 3;
    if (form.message.trim().length < 5) return 4;
    return null;
  };
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (sending.current) return;
    const invalid = invalidStep();
    if (invalid === step || (step === 5 && invalid !== null)) {
      if (step === 5) { setEditing(true); move(invalid!); }
      setFieldError(invalid === 0 ? 'Indiquez au moins deux caractères pour votre nom.' : invalid === 1 ? 'Indiquez une adresse e-mail valide.' : invalid === 4 ? 'Décrivez votre demande en au moins cinq caractères.' : 'Vérifiez les informations de cette étape.');
      return;
    }
    if (step < 5) { move(editing ? 5 : step + 1); setEditing(false); return; }
    sending.current = true;
    setStatus('loading');
    setError('');
    try {
      await submitContactMessage({ ...form, name: form.name.trim(), email: form.email.trim(),
        company: form.company.trim(), phone: form.phone.trim(), message: form.message.trim(),
        privacy_notice_version: '2026-11-13' });
      setStatus('success');
    } catch (failure) {
      setStatus('error');
      setError(failure instanceof Error ? failure.message : 'Le service de contact est indisponible. Vos informations restent sur cette page.');
    } finally { sending.current = false; }
  };
  const edit = (index: number) => { setEditing(true); move(index); };
  const copy = COPY[step];
  const inputProps = { className: 'radar-contact-input', 'aria-invalid': Boolean(fieldError), 'aria-describedby': fieldError ? 'contact-field-error' : undefined };

  return <ForceLightMode><div className="radar-public radar-contact-shell">
    <a href="#main-content" className="sr-only fixed left-4 top-4 z-50 rounded-xl bg-white p-3 text-primary shadow focus:not-sr-only">Aller au contenu</a>
    <ContactNavigation />
    <main id="main-content" className="radar-contact-main">
      <h1 className="sr-only">Contactez l’équipe Radar</h1>
      <div className="radar-contact-frame">
        {isSuccess ? <div ref={panel} className="radar-contact-success" role="status">
          <span className="radar-contact-success-mark"><Check size={28} strokeWidth={1.8} /></span>
          <p className="radar-contact-kicker">La suite commence maintenant</p>
          <h2 tabIndex={-1}>Demande enregistrée.<br /><span>Merci, {form.name.trim().split(/\s+/)[0]}.</span></h2>
          <p>Votre demande est disponible pour notre équipe Radar. Vous recevrez un e-mail lorsque votre dossier sera ouvert.</p>
          <Button asChild className="mt-7 rounded-full px-6"><Link href="/">Retour à l’accueil<ArrowUpRight size={16} className="ml-2" /></Link></Button>
        </div> : <form method="post" onSubmit={submit} aria-describedby="contact-privacy" className="radar-contact-form">
          <noscript><p className="radar-contact-error">Ce formulaire par étapes nécessite JavaScript. Vous pouvez aussi utiliser le <Link href="/legal">contact publié dans les mentions légales</Link>.</p></noscript>
          <div className="radar-contact-progress" role="progressbar" aria-label="Progression du formulaire" aria-valuemin={1} aria-valuemax={6} aria-valuenow={step + 1} aria-valuetext={`${step + 1} sur 6 : ${STEPS[step]}`}>
            {STEPS.map((label, index) => <span key={label} data-reached={index <= step} />)}
          </div>
          <p className="radar-contact-step-count" role="status" aria-live="polite">{String(step + 1).padStart(2, '0')} <span>/ 06</span></p>
          <div ref={panel} key={step} className="radar-contact-step" data-direction={direction}>
            <p className="radar-contact-kicker">{copy.kicker}</p>
            <h2 id="contact-step-title" tabIndex={-1}>{copy.title}<br /><span>{copy.accent}</span></h2>
            <p className="radar-contact-description">{copy.description}</p>
            <div className="radar-contact-fields" aria-labelledby="contact-step-title">
              {step === 0 && <><label htmlFor="contact-name" className="sr-only">Nom complet</label><input {...inputProps} id="contact-name" name="name" autoComplete="name" required minLength={2} maxLength={150} placeholder="Votre prénom et votre nom" value={form.name} onChange={e => update('name', e.target.value)} /></>}
              {step === 1 && <><label htmlFor="contact-email" className="sr-only">Email professionnel</label><input {...inputProps} id="contact-email" name="email" type="email" autoComplete="email" required maxLength={254} placeholder="vous@votre-agence.fr" value={form.email} onChange={e => update('email', e.target.value)} /></>}
              {step === 2 && <div className="space-y-4"><div><label htmlFor="contact-company" className="radar-contact-label">Société <span>facultatif</span></label><input {...inputProps} id="contact-company" name="company" autoComplete="organization" maxLength={200} placeholder="Le nom de votre agence" value={form.company} onChange={e => update('company', e.target.value)} /></div><div><label htmlFor="contact-phone" className="radar-contact-label">Téléphone <span>facultatif</span></label><input {...inputProps} id="contact-phone" name="phone" type="tel" autoComplete="tel" maxLength={40} placeholder="Votre numéro de téléphone" value={form.phone} onChange={e => update('phone', e.target.value)} /></div></div>}
              {step === 3 && <><label htmlFor="contact-plan" className="sr-only">Offre qui vous intéresse, facultatif</label><select {...inputProps} id="contact-plan" name="plan" value={form.plan} onChange={e => update('plan', e.target.value)}>{PLANS.map(plan => <option key={plan.value} value={plan.value}>{plan.label}</option>)}</select><p className="radar-contact-field-hint">Ce choix ne vous engage à aucun abonnement.</p></>}
              {step === 4 && <><label htmlFor="contact-message" className="sr-only">Votre message</label><textarea {...inputProps} id="contact-message" name="message" required minLength={5} maxLength={5000} rows={4} placeholder="Racontez-nous votre besoin…" value={form.message} onChange={e => update('message', e.target.value)} /><p className="radar-contact-field-hint">N’envoyez ni mot de passe, ni clé API, ni donnée sensible.</p></>}
              {step === 5 && <dl className="radar-contact-summary">{[
                { label: 'Nom', value: form.name, index: 0 }, { label: 'E-mail', value: form.email, index: 1 },
                { label: 'Agence et téléphone', value: [form.company, form.phone].filter(Boolean).join(' · ') || 'Non renseignés', index: 2 },
                { label: 'Offre', value: PLANS.find(plan => plan.value === form.plan)?.label, index: 3 },
                { label: 'Message', value: form.message, index: 4 },
              ].map(row => <div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd><button type="button" disabled={status === 'loading'} aria-label={`Modifier : ${row.label}`} onClick={() => edit(row.index)}>Modifier</button></div>)}</dl>}
              {fieldError && <p id="contact-field-error" role="alert" className="radar-contact-error">{fieldError}</p>}
              {step === 5 && error && <p role="alert" className="radar-contact-error">{error}</p>}
              <Button type="submit" disabled={!ready || status === 'loading'} className="radar-contact-continue">{status === 'loading' ? <><RadarSpinner size={16} className="animate-spin" />Envoi en cours…</> : step === 5 ? <>Envoyer le message<Send size={15} /></> : <>{editing ? 'Valider la modification' : 'Continuer'}<ArrowRight size={16} /></>}</Button>
            </div>
          </div>
          <div className="radar-contact-bottomline">{step > 0 ? <button type="button" disabled={status === 'loading'} onClick={() => { move(editing ? 5 : step - 1); setEditing(false); }}><ArrowLeft size={14} />{editing ? 'Récapitulatif' : 'Précédent'}</button> : <span aria-hidden="true" />}<span>{step === 5 ? 'Un envoi, après votre confirmation.' : step === 4 ? 'Puis, vérifiez votre demande.' : 'Entrée pour continuer'}</span></div>
        </form>}
      </div>
      <div className="radar-contact-caption"><p id="contact-privacy">Nom, e-mail et message : pour répondre à votre demande professionnelle. Société, téléphone et offre sont facultatifs. Aucune inscription à une newsletter. <Link href="/privacy#contact">Utilisation des données et vos droits<ArrowUpRight size={11} /></Link></p></div>
    </main>
  </div></ForceLightMode>;
}
