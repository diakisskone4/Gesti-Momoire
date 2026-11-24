import { useCallback, useEffect, useState } from 'react';

import { describeError } from '../../api/client';
import { adminPaymentsApi } from '../../api/services';
import Modal from '../../components/Modal';
import { useToast } from '../../context/ToastContext';
import { formatDate, formatPrice } from '../../lib/format';
import type { AdminPayment, PaymentDevice } from '../../lib/models';

export const OPERATOR_LABELS: Record<string, string> = { orange: 'Orange Money', moov: 'Moov Money', wave: 'Wave' };
const STATUS: Record<string, [string, string]> = {
  SUBMITTED: ['À vérifier', 'DRAFT'], PAID: ['Payé', 'VALIDATED'], FAILED: ['Refusé', 'ARCHIVED'], CANCELLED: ['Annulé', 'ARCHIVED'],
};
const ONLINE_MS = 45 * 60 * 1000; // l'application se signale environ toutes les 15 minutes

/** Paiements mobile money : vérification par l'administrateur et téléphones d'encaissement. */
export default function AdminPayments({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const [payments, setPayments] = useState<AdminPayment[] | null>(null);
  const [devices, setDevices] = useState<PaymentDevice[]>([]);
  const [all, setAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [token, setToken] = useState('');

  const load = useCallback(() => {
    Promise.all([adminPaymentsApi.list(all), adminPaymentsApi.devices()])
      .then(([list, phones]) => { setPayments(list); setDevices(phones); setError(''); })
      .catch(err => setError(describeError(err, 'Impossible de charger les paiements.')));
  }, [all]);
  useEffect(load, [load]);

  const run = async (work: () => Promise<unknown>, success: string) => {
    setBusy(true);
    try {
      await work();
      toast.success(success);
      onChanged();
    } catch (err) {
      toast.error('Action impossible', describeError(err));
    } finally {
      setBusy(false);
      load();
    }
  };

  const approve = (p: AdminPayment, messageId?: number) => {
    const question = messageId
      ? `Confirmer le paiement de ${p.buyer_name} avec ce message ?`
      : `Avez-vous vérifié sur votre compte ${OPERATOR_LABELS[p.operator]} que ${formatPrice(p.amount, p.currency)} sont bien arrivés du ${p.payer_phone} ?\n\nLe modèle sera débloqué définitivement.`;
    if (window.confirm(question)) run(() => adminPaymentsApi.approve(p.id, messageId), 'Paiement confirmé');
  };

  const reject = (p: AdminPayment) => {
    const reason = window.prompt('Raison du refus (envoyée au client) :', "Aucun transfert correspondant n'a été reçu.")?.trim();
    if (reason) run(() => adminPaymentsApi.reject(p.id, reason), 'Paiement refusé');
  };

  const pair = () => run(async () => {
    const device = await adminPaymentsApi.pair('Téléphone d\'encaissement');
    setToken(device.token);
  }, 'Téléphone créé');

  const revoke = (d: PaymentDevice) => {
    if (window.confirm(`Retirer « ${d.name} » ? Il ne pourra plus transmettre les paiements.`)) {
      run(() => adminPaymentsApi.revoke(d.id), 'Téléphone retiré');
    }
  };

  return (
    <>
      <div className="ws-head">
        <div><h2 style={{ fontSize: 20 }}>Paiements mobile money</h2></div>
        <button className="btn" onClick={load}>↻ Actualiser</button>
      </div>
      <div className="toolbar">
        <div className="tabs" role="tablist">
          <button className={`tab${all ? '' : ' active'}`} role="tab" aria-selected={!all} onClick={() => setAll(false)}>À vérifier</button>
          <button className={`tab${all ? ' active' : ''}`} role="tab" aria-selected={all} onClick={() => setAll(true)}>Tous</button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="table-wrap">
        <table className="cards-mobile">
          <thead><tr><th>Client</th><th>Modèle</th><th className="num">Montant</th><th>Paiement déclaré</th><th>Statut</th><th /></tr></thead>
          <tbody>
            {payments === null && <tr><td colSpan={6} className="muted">Chargement...</td></tr>}
            {payments?.length === 0 && <tr><td colSpan={6} className="muted">{all ? 'Aucun paiement.' : 'Aucun paiement à vérifier.'}</td></tr>}
            {payments?.map(p => (
              <tr key={p.id}>
                <td className="cell-title" data-label="Client"><strong>{p.buyer_name}</strong><br /><span className="muted">{p.buyer_email}</span></td>
                <td data-label="Modèle">{p.template_name}</td>
                <td className="num" data-label="Montant">{formatPrice(p.amount_charged ?? p.amount, p.currency)}</td>
                <td data-label="Paiement">
                  <span>{OPERATOR_LABELS[p.operator]} · {p.payer_phone}<br /><code>{p.transaction_reference}</code><br />
                    <span className="muted">{p.submitted_at ? formatDate(p.submitted_at) : ''}</span></span>
                </td>
                <td data-label="Statut">
                  <span className={`badge ${STATUS[p.status]?.[1] ?? ''}`}>{STATUS[p.status]?.[0] ?? p.status}</span>
                  {p.automatic && <span className="muted"> automatique</span>}
                </td>
                <td className="cell-actions" style={{ flexWrap: 'wrap', gap: 6 }}>
                  {p.suggestions.map(m => (
                    <button key={m.id} className="mm-message" disabled={busy} onClick={() => approve(p, m.id)}>
                      Message reçu : « {m.text} »<strong> Confirmer avec ce message</strong>
                    </button>
                  ))}
                  {(p.status === 'SUBMITTED' || p.status === 'FAILED') && (
                    <button className="btn primary" disabled={busy} onClick={() => approve(p)}>Confirmer</button>
                  )}{' '}
                  {p.status === 'SUBMITTED' && <button className="btn danger" disabled={busy} onClick={() => reject(p)}>Refuser</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="panel">
        <h3>Téléphones d'encaissement</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          L'application Android « MemoAI Encaissement », installée sur le téléphone qui reçoit l'argent, confirme les
          paiements automatiquement. Sans elle, confirmez chaque paiement ci-dessus.
        </p>
        {devices.map(d => {
          const online = d.last_seen_at && Date.now() - new Date(d.last_seen_at).getTime() < ONLINE_MS;
          return (
            <p key={d.id} className="mm-device">
              <span>{online ? '🟢' : '⚪'} <strong>{d.name}</strong>{' '}
                <span className="muted">{d.last_seen_at ? `vu le ${new Date(d.last_seen_at).toLocaleString('fr-FR')}` : 'jamais connecté'}</span></span>
              <button className="btn danger" disabled={busy} onClick={() => revoke(d)}>Retirer</button>
            </p>
          );
        })}
        <button className="btn primary" disabled={busy} onClick={pair}>＋ Associer un téléphone</button>
      </section>

      {token && (
        <Modal title="Associer le téléphone" onClose={() => setToken('')} footer={<button className="btn-primary" onClick={() => setToken('')}>Terminé</button>}>
          <div className="alert info">Ce code n'est affiché qu'une seule fois. Ne le partagez avec personne : il permet de confirmer des paiements.</div>
          <p>Si cette page est ouverte sur le téléphone d'encaissement :{' '}
            <a className="btn-primary" style={{ display: 'inline-block', marginTop: 8 }} href={`memoai-encaissement://jumeler?jeton=${token}`}>Associer ce téléphone</a></p>
          <p>Sinon, recopiez ce code dans l'application « MemoAI Encaissement » :</p>
          <code className="mm-token">{token}</code>
          <button className="btn-secondary" onClick={() => navigator.clipboard?.writeText(token).then(() => toast.success('Code copié'), () => undefined)}>Copier le code</button>
        </Modal>
      )}
    </>
  );
}
