import { useState } from 'react';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { ArrowUpRight, AlertCircle } from 'lucide-react';
import { API_BASE } from '../constants';

export const PayoutForm = ({ selectedMerchant, fetchData }) => {
  const [amount, setAmount] = useState('');
  const [bankAccount, setBankAccount] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!amount || !bankAccount || !selectedMerchant) return;

    setLoading(true);
    setError(null);
    try {
      const idempotencyKey = uuidv4();
      await axios.post(`${API_BASE}/payouts`, {
        merchant_id: selectedMerchant.id,
        amount_paise: Math.round(parseFloat(amount) * 100),
        bank_account_id: bankAccount
      }, {
        headers: {
          'Idempotency-Key': idempotencyKey,
          'Content-Type': 'application/json'
        }
      });

      setAmount('');
      setBankAccount('');
      fetchData();
    } catch (error) {
      setError(error.response?.data?.error || `Payout failed ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="md:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <ArrowUpRight className="w-5 h-5 mr-2 text-indigo-400" />
        Request New Payout
      </h3>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-1.5">
          <label className="text-xs text-slate-500 uppercase font-bold ml-1">Amount (INR)</label>
          <input
            type="number"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
            placeholder="0.00"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-xs text-slate-500 uppercase font-bold ml-1">Bank Account</label>
          <input
            type="text"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all"
            placeholder="IFSC / ACC NO"
            value={bankAccount}
            onChange={(event) => setBankAccount(event.target.value)}
          />
        </div>
        <div className="flex items-end">
          <button
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-2.5 rounded-lg transition-all shadow-lg shadow-indigo-500/20 active:scale-[0.98]"
          >
            {loading ? 'Processing...' : 'Initiate Payout'}
          </button>
        </div>
      </form>
      {error && (
        <p className="mt-4 text-rose-500 text-sm flex items-center">
          <AlertCircle className="w-4 h-4 mr-1.5" />
          {error}
        </p>
      )}
    </div>
  );
};
