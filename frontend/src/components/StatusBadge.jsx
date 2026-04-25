import { RefreshCcw, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { PAYOUT_STATUS } from '../constants';

export const StatusBadge = ({ status }) => {
  const styles = {
    [PAYOUT_STATUS.PENDING]: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    [PAYOUT_STATUS.PROCESSING]: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    [PAYOUT_STATUS.COMPLETED]: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    [PAYOUT_STATUS.FAILED]: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
  };
  const icons = {
    [PAYOUT_STATUS.PENDING]: <Clock className="w-3 h-3 mr-1" />,
    [PAYOUT_STATUS.PROCESSING]: <RefreshCcw className="w-3 h-3 mr-1 animate-spin" />,
    [PAYOUT_STATUS.COMPLETED]: <CheckCircle2 className="w-3 h-3 mr-1" />,
    [PAYOUT_STATUS.FAILED]: <AlertCircle className="w-3 h-3 mr-1" />,
  };

  return (
    <span className={`flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status]}`}>
      {icons[status]}
      {status}
    </span>
  );
};
