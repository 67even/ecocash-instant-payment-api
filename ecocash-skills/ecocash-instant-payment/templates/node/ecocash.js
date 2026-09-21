import { randomUUID } from 'node:crypto';

const cfg = {
  baseUrl: (process.env.EIP_BASE_URL ?? 'https://developers.ecocash.co.zw/sandbox/payment/v1').replace(/\/+$/, ''),
  auth: 'Basic ' + Buffer.from(`${process.env.EIP_USERNAME}:${process.env.EIP_PASSWORD}`).toString('base64'),
  refundTranType: process.env.EIP_REFUND_TRAN_TYPE ?? 'REF',
};

const merchant = () => ({
  merchantCode: process.env.EIP_MERCHANT_CODE,
  merchantPin: process.env.EIP_MERCHANT_PIN,
  merchantNumber: process.env.EIP_MERCHANT_NUMBER,
  countryCode: 'ZW',
  terminalID: process.env.EIP_TERMINAL_ID,
  location: process.env.EIP_LOCATION ?? 'Harare',
  superMerchantName: process.env.EIP_SUPER_MERCHANT_NAME,
  merchantName: process.env.EIP_MERCHANT_NAME,
});

const paymentAmount = (amount, currency, description) => ({
  charginginformation: { amount: Number(amount).toFixed(2), currency, description }, // "2.00" - section 4.5
  chargeMetaData: { channel: process.env.EIP_CHANNEL ?? 'WEB' },
});

async function eip(path, init = {}) {
  const res = await fetch(cfg.baseUrl + path, {
    ...init,
    headers: { Authorization: cfg.auth, 'Content-Type': 'application/json', Accept: 'application/json' },
    signal: AbortSignal.timeout(30_000),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(`EIP ${res.status}: ${body.statusMessage ?? 'request failed'}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

/** Start a charge. Persist `correlator` BEFORE calling this. */
export function charge({ msisdn, amount, currency = 'USD', reference, correlator, notifyUrl = '' }) {
  return eip('/transactions/amount/', {
    method: 'POST',
    body: JSON.stringify({
      clientCorrelator: correlator,
      notifyUrl,
      referenceCode: reference,
      tranType: 'MER',
      endUserId: msisdn,
      remarks: reference,
      transactionOperationStatus: 'Charged',
      paymentAmount: paymentAmount(amount, currency, reference),
      ...merchant(),
    }),
  });
}

export function lookup(msisdn, correlator) {
  return eip(`/${encodeURIComponent(msisdn)}/transactions/amount/${encodeURIComponent(correlator)}`);
}

export function refund({ msisdn, originalReference, amount, currency = 'USD', reference }) {
  return eip('/transactions/refund/', {
    method: 'POST',
    body: JSON.stringify({
      clientCorrelator: randomUUID(), // a NEW correlator
      referenceCode: reference,
      tranType: cfg.refundTranType,
      endUserId: msisdn,
      originalEcocashReference: originalReference,
      remarks: reference,
      paymentAmount: paymentAmount(amount, currency, 'Refund'),
      ...merchant(),
    }),
  });
}

/** `status` is documented; the SDK samples read two other names. */
export const statusOf = (b) => b.status ?? b.transactionStatus ?? b.transactionOperationStatus ?? null;
export const referenceOf = (b) => b.ecocashReference ?? b.transactionId ?? null;

/** Poll every 3 s until the status is final or the timeout passes. */
export async function waitForResult(msisdn, correlator, timeoutMs = 90_000) {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    const s = statusOf(await lookup(msisdn, correlator));
    if (s === 'SUCCESS' || s === 'FAILED') return s;
    await new Promise((r) => setTimeout(r, 3_000));
  }
  return 'UNKNOWN'; // not final: flag for review, never assume failure
}
