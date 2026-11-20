/** Public contact uses the site's API proxy, without account/workspace state. */
const unavailable = 'Le service de contact est temporairement indisponible. Vos informations restent sur cette page ; réessayez ou utilisez le contact des mentions légales.';

export async function submitContactMessage(data: Record<string, string>) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 35000);
  try {
    const response = await fetch('/api/v1/contact', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data), signal: controller.signal,
    });
    const payload = await response.json().catch(() => null);
    if (response.ok && payload?.status === 'ok') return;
    if (response.status === 422) throw new Error('Vérifiez le format de vos informations, notamment votre adresse e-mail. Votre demande reste sur cette page.');
    if (response.status === 429) throw new Error('Trop de tentatives rapprochées. Patientez avant de réessayer ; vos informations sont conservées sur cette page.');
    const reference = payload?.detail?.code === 'CONTACT_UNAVAILABLE' && /^[a-f0-9]{12}$/.test(payload?.detail?.reference || '') ? ` Référence : ${payload.detail.reference}.` : '';
    throw new Error(unavailable + reference);
  } catch (failure) {
    if (failure instanceof Error && (failure.message.startsWith(unavailable) || failure.message.startsWith('Vérifiez le format') || failure.message.startsWith('Trop de tentatives'))) throw failure;
    throw new Error('La connexion au service de contact a échoué ou a expiré. Vos informations restent sur cette page ; vérifiez votre connexion puis réessayez.');
  } finally { clearTimeout(timeout); }
}
