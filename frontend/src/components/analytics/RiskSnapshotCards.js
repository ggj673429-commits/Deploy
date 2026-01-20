/**
 * Risk Snapshot Cards Component
 * Displays risk exposure metrics on admin dashboard
 * Uses centralized admin API client
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { DollarSign, TrendingUp, AlertTriangle, ChevronRight, Clock } from 'lucide-react';

// Centralized Admin API
import { analyticsApi } from '../../api/admin';

// Helper: Safe money formatting
const toMoney = (value) => {
  const num = Number(value || 0);
  return isNaN(num) ? 0 : num;
};

const RiskSnapshotCards = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const fetchRiskSnapshot = useCallback(async () => {
    try {
      const response = await analyticsApi.getRiskSnapshot();
      setData(response.data);
    } catch (err) {
      console.error('Failed to fetch risk snapshot:', err);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRiskSnapshot();
  }, [fetchRiskSnapshot]);

  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 animate-pulse">
            <div className="h-4 w-24 bg-gray-700 rounded mb-3"></div>
            <div className="h-8 w-32 bg-gray-700 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div data-testid="risk-snapshot-cards">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-400" />
            Risk & Exposure
          </h2>
        </div>
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 text-center">
          <p className="text-gray-500 text-sm">Risk data unavailable</p>
        </div>
      </div>
    );
  }

  const pressureColors = {
    low: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400' },
    medium: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400' },
    high: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400' }
  };

  const pressure = data?.cashout_pressure?.indicator || 'low';
  const pressureStyle = pressureColors[pressure];

  return (
    <div data-testid="risk-snapshot-cards">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-orange-400" />
          Risk & Exposure
        </h2>
        <Link to="/admin/reports?tab=risk" className="text-gray-500 hover:text-emerald-400 text-sm flex items-center gap-1">
          View Details <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Card 1: Total Client Balance */}
        <Link to="/admin/reports?tab=risk" className="group" data-testid="total-client-balance-card">
          <div className="bg-gray-900/50 border border-gray-800 hover:border-blue-500/30 rounded-xl p-5 transition-all h-full">
            <div className="flex items-center justify-between mb-3">
              <span className="text-blue-400/80 text-sm font-medium">Total Client Balance</span>
              <DollarSign className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-white mb-1" data-testid="total-client-balance-value">
              ${toMoney(data?.total_client_balance?.combined).toLocaleString()}
            </p>
            <p className="text-gray-500 text-xs">
              Cash: ${toMoney(data?.total_client_balance?.cash).toLocaleString()} • 
              Bonus: ${toMoney(data?.total_client_balance?.bonus).toLocaleString()}
            </p>
          </div>
        </Link>

        {/* Card 2: Risk Max 24h - MAX(deposit * multiplier) from last 24h */}
        <Link to="/admin/reports?tab=risk" className="group" data-testid="risk-max-24h-card">
          <div className="bg-gray-900/50 border border-gray-800 hover:border-purple-500/30 rounded-xl p-5 transition-all h-full">
            <div className="flex items-center justify-between mb-3">
              <span className="text-purple-400/80 text-sm font-medium">Risk Max 24h</span>
              <Clock className="w-4 h-4 text-purple-400" />
            </div>
            <p className="text-2xl font-bold text-purple-400 mb-1" data-testid="risk-max-24h-value">
              ${toMoney(data?.risk_max_24h?.amount).toLocaleString()}
            </p>
            <p className="text-gray-500 text-xs">
              @{data?.risk_max_24h?.max_multiplier_used || 3}x cap • MAX from 24h deposits
            </p>
          </div>
        </Link>

        {/* Card 3: Cashout Pressure */}
        <Link to="/admin/reports?tab=risk" className="group" data-testid="cashout-pressure-card">
          <div className={`${pressureStyle.bg} border ${pressureStyle.border} rounded-xl p-5 transition-all h-full hover:opacity-90`}>
            <div className="flex items-center justify-between mb-3">
              <span className={`${pressureStyle.text} text-sm font-medium opacity-80`}>Cashout Pressure</span>
              <AlertTriangle className={`w-4 h-4 ${pressureStyle.text}`} />
            </div>
            <p className={`text-2xl font-bold ${pressureStyle.text} mb-1 uppercase`} data-testid="cashout-pressure-value">
              {pressure}
            </p>
            <p className="text-gray-500 text-xs">
              {data?.cashout_pressure?.pending_count || 0} pending • ${toMoney(data?.cashout_pressure?.pending_amount).toLocaleString()}
            </p>
          </div>
        </Link>
      </div>
    </div>
  );
};

export default RiskSnapshotCards;
