import { useEffect, useRef, useState, type FormEvent } from 'react';

import { describeError } from '../../api/client';
import { modelesApi } from '../../api/services';
import Modal from '../../components/Modal';
import { formatPrice } from '../../lib/format';
import type { OperatorCode, PaymentOptions, TemplatePurchase } from '../../lib/models';

interface Props {
  purchase: TemplatePurchase;
  options: PaymentOptions;
  onClose: () => void;
  /** Appelé à chaque changement d'état de l'achat. */
  onUpdate: (purchase: TemplatePurchase) => void;
}

/** Paiement direct par Orange Money, Moov Money ou Wave : envoyer l'argent, puis déclarer la référence. */
export default function MobileMoneyModal({ purchase, options, onClose, onUpdate }: Props) {
  const [operator, setOperator] = useState<OperatorCode | ''>(purchase.operator);
  const [phone, setPhone] = useState(purchase.payer_phone);
  const [reference, setReference] = useState(purchase.transaction_reference);
  const [editing, setEditing] = useState(purchase.status === 'PENDING');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const update = useRef(onUpdate);
  update.current = onUpdate;

  const waiting = purchase.status === 'SUBMITTED' && !editing;
  useEffect(() => {
    if (!waiting) return;
    const timer = window.setInterval(() => {
      modelesApi.verify(purchase.id).then(p => update.current(p)).catch(() => undefined);
    }, 10000);
    return () => window.clearInterval(timer);
  }, [waiting, purchase.id]);

  const info = options.operators?.find(o => o.code === operator);
  const amount = formatPrice(purchase.amount, purchase.currency);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(info?.number ?? '');
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Copie impossible : recopiez le numéro à la main.');
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!operator) return;
    setBusy(true);
    setError('');
    try {
      const updated = await modelesApi.declare(purchase.id, { operator, phone, reference });
      setEditing(false);
      update.current(updated);
    } catch (err) {
      setError(describeError(err, "Votre paiement n'a pas pu être enregistré."));
    } finally {
      setBusy(false);
    }
  };

  if (purchase.status === 'PAID') {
    return (
      <Modal title="Paiement confirmé" onClose={onClose} footer={<button className="btn-primary" onClick={onClose}>Continuer</button>}>
        <div className="alert success">✅ « {purchase.template_name} » est à vous. Cliquez sur « Utiliser ce modèle ».</div>
      </Modal>
    );
  }
  if (purchase.status === 'FAILED' || purchase.status === 'CANCELLED') {
    return (
      <Modal title="Paiement non confirmé" onClose={onClose} footer={<button className="btn-primary" onClick={onClose}>Fermer</button>}>
        <div className="alert error">{purchase.review_note || "Le paiement n'a pas été confirmé. Vous pouvez relancer l'achat."}</div>
      </Modal>
    );
  }
  if (waiting) {
    return (
      <Modal title="Paiement en vérification" onClose={onClose} footer={<>
        <button className="btn-secondary" onClick={() => setEditing(true)}>Corriger ma déclaration</button>
        <button className="btn-primary" onClick={onClose}>Fermer</button>
      </>}>
        <div className="alert info" role="status">
          ⏳ Nous vérifions l'arrivée de vos {amount}. Vous pouvez fermer cette fenêtre : une notification vous préviendra.
        </div>
        <ul className="mm-recap">
          <li><span>Modèle</span><strong>{purchase.template_name}</strong></li>
          <li><span>Opérateur</span><strong>{info?.label}</strong></li>
          <li><span>Numéro payeur</span><strong>{purchase.payer_phone}</strong></li>
          <li><span>Référence</span><strong>{purchase.transaction_reference}</strong></li>
        </ul>
      </Modal>
    );
  }

  return (
    <Modal title={`Payer ${amount}`} onClose={onClose} footer={<>
      <button type="button" className="btn-secondary" onClick={onClose}>Plus tard</button>
      <button type="submit" form="mm-form" className="btn-primary" disabled={busy || !operator}>
        {busy ? 'Envoi…' : "J'ai payé"}
      </button>
    </>}>
      <form id="mm-form" onSubmit={submit}>
        <p className="muted" style={{ marginTop: 0 }}>Modèle « {purchase.template_name} »</p>
        <div className="mm-operators" role="radiogroup" aria-label="Opérateur">
          {options.operators?.map(o => (
            <button key={o.code} type="button" role="radio" aria-checked={operator === o.code}
                    className={`mm-operator ${o.code}${operator === o.code ? ' active' : ''}`} onClick={() => { setOperator(o.code); setCopied(false); }}>
              {o.label}
            </button>
          ))}
        </div>

        {info && (
          <>
            <ol className="mm-steps">
              <li>{info.steps}{info.ussd && <> <a href={`tel:${encodeURIComponent(info.ussd)}`}>Composer {info.ussd}</a></>}</li>
              <li>
                Envoyez <strong>{amount}</strong> au numéro :
                <span className="mm-number">
                  <strong>{info.number_display}</strong>
                  <button type="button" className="btn-secondary" onClick={copy}>{copied ? 'Copié ✓' : 'Copier'}</button>
                </span>
                {options.holder && <>Vérifiez le nom du bénéficiaire : <strong>{options.holder}</strong>.</>}
              </li>
              <li>Recopiez ci-dessous la référence (identifiant de transaction) donnée par {info.label}.</li>
            </ol>
            <p className="muted small">Les frais d'envoi éventuels de l'opérateur sont à votre charge : nous devons recevoir {amount}.</p>
            <label className="form-field">Votre numéro {info.label}
              <input type="tel" inputMode="tel" autoComplete="tel-national" required maxLength={20} placeholder="76 12 34 56"
                     value={phone} onChange={e => setPhone(e.target.value)} />
            </label>
            <label className="form-field">Référence de la transaction
              <input required maxLength={40} autoComplete="off" autoCapitalize="characters" placeholder="Identifiant reçu après le paiement"
                     value={reference} onChange={e => setReference(e.target.value)} />
            </label>
          </>
        )}
        {error && <div className="alert error">⚠ {error}</div>}
      </form>
    </Modal>
  );
}
