import { Wallet } from 'lucide-react';
import { formatINR } from '../utils';

export const BalanceCards = ({ balance, heldBalance }) => {
  return (
    <div className="md:col-span-1 space-y-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
        <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:scale-110 transition-transform">
          <Wallet className="w-24 h-24 text-indigo-500" />
        </div>
        <div className="relative z-10">
          <p className="text-slate-500 text-sm font-medium">Available Balance</p>
          <h2 className="text-4xl font-bold mt-2 text-white tabular-nums">
            {balance !== null ? formatINR(balance) : '---'}
          </h2>
          <div className="mt-4 flex items-center text-emerald-400 text-sm">
            <div className="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse" />
            Live from Ledger
          </div>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <p className="text-slate-500 text-sm font-medium">Held Funds (Processing)</p>
        <h2 className="text-2xl font-semibold mt-1 text-slate-300 tabular-nums">
          {heldBalance !== null ? formatINR(heldBalance) : '---'}
        </h2>
      </div>
    </div>
  );
};
