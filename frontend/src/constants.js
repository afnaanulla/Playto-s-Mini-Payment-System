export const API_BASE = '/api/v1';

// NOTE: Since native JavaScript lacks Enums, we use Object.freeze() 
// to create strict, immutable constant objects. This prevents typos 
// and accidental mutations, mimicking the behavior of an Enum.
export const PAYOUT_STATUS = Object.freeze({
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
});

export const LEDGER_ENTRY_TYPE = Object.freeze({
  CREDIT: 'CR',
  DEBIT: 'DR',
});
