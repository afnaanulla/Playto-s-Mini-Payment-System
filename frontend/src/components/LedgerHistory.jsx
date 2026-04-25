import { Wallet } from 'lucide-react';
import { formatINR } from '../utils';
import { LEDGER_ENTRY_TYPE } from '../constants';

export const LedgerHistory = ({ ledger }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="p-6 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center">
          <Wallet className="w-5 h-5 mr-2 text-emerald-400" />
          Ledger (Credits & Debits)
        </h3>
      </div>
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full text-left">
          <thead className="bg-slate-950/50 text-slate-500 text-xs uppercase sticky top-0">
            <tr>
              <th className="px-6 py-4 font-bold">Type</th>
              <th className="px-6 py-4 font-bold">Description</th>
              <th className="px-6 py-4 font-bold text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {ledger.length > 0 ? ledger.map(entry => (
              <tr key={entry.id} className="hover:bg-slate-800/20 transition-colors">
                <td className="px-6 py-4">
                  <span className={`text-xs font-bold ${entry.entry_type === LEDGER_ENTRY_TYPE.CREDIT ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {entry.entry_type_display.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-300 text-sm">
                  {entry.description}
                </td>
                <td className={`px-6 py-4 text-right font-semibold ${entry.entry_type === LEDGER_ENTRY_TYPE.CREDIT ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {entry.entry_type === LEDGER_ENTRY_TYPE.CREDIT ? '+' : '-'}{formatINR(entry.amount_paise)}
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan="3" className="px-6 py-12 text-center text-slate-500">
                  No ledger entries found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
