import { History } from 'lucide-react';
import { formatINR } from '../utils';
import { StatusBadge } from './StatusBadge';

export const PayoutHistory = ({ payouts }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center">
          <History className="w-5 h-5 mr-2 text-indigo-400" />
          Payout History
        </h3>
      </div>
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full text-left">
          <thead className="bg-slate-950/50 text-slate-500 text-xs uppercase sticky top-0">
            <tr>
              <th className="px-6 py-4 font-bold">Transaction ID</th>
              <th className="px-6 py-4 font-bold text-right">Amount</th>
              <th className="px-6 py-4 font-bold">Bank Account</th>
              <th className="px-6 py-4 font-bold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {payouts.length > 0 ? payouts.map(payout => (
              <tr key={payout.id} className="hover:bg-slate-800/20 transition-colors">
                <td className="px-6 py-4 font-mono text-sm text-slate-400">
                  {payout.id.slice(0, 8)}...
                </td>
                <td className="px-6 py-4 text-right font-semibold text-white">
                  {formatINR(payout.amount_paise)}
                </td>
                <td className="px-6 py-4 font-mono text-sm text-slate-400">
                  {payout.bank_account_id}
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={payout.status} />
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan="3" className="px-6 py-12 text-center text-slate-500">
                  No payouts found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
