import { ChevronDown } from 'lucide-react';

export const Header = ({ merchants, selectedMerchant, setSelectedMerchant }) => {
  return (
    <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
          Playto Payout Engine
        </h1>
        <p className="text-slate-500 mt-1">Real-time Merchant Dashboard</p>
      </div>

      <div className="relative group">
        <select
          className="appearance-none bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all cursor-pointer"
          value={selectedMerchant?.id || ''}
          onChange={(event) => setSelectedMerchant(merchants.find(merchant => merchant.id === event.target.value))}
        >
          {merchants.map(merchant => (
            <option key={merchant.id} value={merchant.id}>{merchant.name}</option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
      </div>
    </header>
  );
};
