import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_BASE } from './constants';
import { Header } from './components/Header';
import { BalanceCards } from './components/BalanceCards';
import { PayoutForm } from './components/PayoutForm';
import { PayoutHistory } from './components/PayoutHistory';
import { LedgerHistory } from './components/LedgerHistory';

function App() {
  const [merchants, setMerchants] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState(null);
  const [balance, setBalance] = useState(null);
  const [heldBalance, setHeldBalance] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [error, setError] = useState(null);

  // Fetch all merchants on mount
  useEffect(() => {
    axios.get(`${API_BASE}/merchants`)
      .then(response => {
        setMerchants(response.data);
        if (response.data.length > 0) setSelectedMerchant(response.data[0]);
      })
      .catch(error => setError(`Failed to load merchants ${error}`));
  }, []);

  // Fetch balance, payouts, and ledger
  const fetchData = useCallback(async () => {
    if (!selectedMerchant) return;
    try {
      const [balResponse, payResponse, ledgerResponse] = await Promise.all([
        axios.get(`${API_BASE}/merchants/${selectedMerchant.id}/balance`),
        axios.get(`${API_BASE}/merchants/${selectedMerchant.id}/payouts`),
        axios.get(`${API_BASE}/merchants/${selectedMerchant.id}/ledger`)
      ]);
      setBalance(balResponse.data.available_paise);
      setHeldBalance(balResponse.data.held_paise);
      setPayouts(payResponse.data);
      setLedger(ledgerResponse.data);
    } catch (error) {
      setError(`Failed to sync live data. Please try again later. ${error}`);
    }
  }, [selectedMerchant]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Poll every 10 seconds
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 text-rose-500 p-4 rounded-xl text-sm font-medium">
            {error}
          </div>
        )}

        <Header 
          merchants={merchants} 
          selectedMerchant={selectedMerchant} 
          setSelectedMerchant={setSelectedMerchant} 
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <BalanceCards balance={balance} heldBalance={heldBalance} />
          <PayoutForm selectedMerchant={selectedMerchant} fetchData={fetchData} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PayoutHistory payouts={payouts} />
          <LedgerHistory ledger={ledger} />
        </div>
      </div>
    </div>
  );
}

export default App;
