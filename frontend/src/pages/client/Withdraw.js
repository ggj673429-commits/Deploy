/**
 * Withdraw - Production-grade withdrawal flow
 * Route: /client/wallet/withdraw
 * 
 * Features:
 * - Amount input with balance validation
 * - Withdrawal method selection
 * - Account details
 * - Idempotency for submit
 * - Cashout preview (best-effort)
 * - Success state with order ID and tracking CTA
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  DollarSign, Building2, CheckCircle, Loader2, AlertCircle,
  ArrowLeft, Info, History, AlertTriangle, Wallet
} from 'lucide-react';

// Centralized API
import http, { getErrorMessage, isServerUnavailable } from '../../api/http';
import { PageLoader } from '../../features/shared/LoadingStates';
import { toNumber, toMoney } from '../../utils/normalize';
import { generateIdempotencyKey, withIdempotency } from '../../utils/idempotency';

// Minimum withdrawal amount (can be configured)
const MIN_WITHDRAWAL_AMOUNT = 10;

const withdrawalMethods = [
  { id: 'gcash', name: 'GCash' },
  { id: 'paymaya', name: 'PayMaya' },
  { id: 'bank', name: 'Bank Transfer' },
];

const Withdraw = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1);
  const [walletData, setWalletData] = useState(null);
  const [amount, setAmount] = useState('');
  const [amountError, setAmountError] = useState(null);
  const [method, setMethod] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [accountName, setAccountName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [orderId, setOrderId] = useState(null);
  const [orderStatus, setOrderStatus] = useState(null);
  const [error, setError] = useState(null);
  
  // Cashout preview state
  const [cashoutPreview, setCashoutPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  
  // Idempotency and double-submit prevention
  const idempotencyKeyRef = useRef(null);
  const isSubmittingRef = useRef(false);

  const fetchWallet = useCallback(async () => {
    setLoading(true);
    try {
      const response = await http.get('/wallet/balance');
      setWalletData(response.data);
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to load wallet');
      toast.error(message);
      // Set default
      setWalletData({ cash_balance: 0, wallet_balance: 0, real_balance: 0 });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWallet();
  }, [fetchWallet]);

  // Get withdrawable balance with fallbacks
  const getWithdrawableBalance = () => {
    if (!walletData) return 0;
    // Priority: withdrawable > cash_balance > wallet_balance > real_balance
    return toNumber(
      walletData.withdrawable ?? 
      walletData.cash_balance ?? 
      walletData.wallet_balance ?? 
      walletData.real_balance
    );
  };
  
  const withdrawableBalance = getWithdrawableBalance();

  // Fetch cashout preview when amount changes
  const fetchCashoutPreview = useCallback(async (withdrawAmount) => {
    if (!withdrawAmount || withdrawAmount <= 0) {
      setCashoutPreview(null);
      return;
    }
    
    setPreviewLoading(true);
    setPreviewError(null);
    
    try {
      const response = await http.post('/wallet/cashout-preview', {
        amount: withdrawAmount
      });
      
      if (response.data) {
        setCashoutPreview(response.data);
      }
    } catch (err) {
      // Best-effort - don't block withdrawal if preview fails
      console.warn('Cashout preview failed:', err);
      setPreviewError('Preview unavailable');
      setCashoutPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  // Debounced preview fetch
  useEffect(() => {
    const parsed = parseFloat(amount);
    if (Number.isFinite(parsed) && parsed > 0 && parsed <= withdrawableBalance) {
      const timer = setTimeout(() => {
        fetchCashoutPreview(parsed);
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setCashoutPreview(null);
    }
  }, [amount, withdrawableBalance, fetchCashoutPreview]);

  // Validate amount
  const validateAmount = (value) => {
    const parsed = parseFloat(value);
    
    if (!value || value === '') {
      return null; // No error for empty
    }
    
    if (!Number.isFinite(parsed)) {
      return 'Please enter a valid number';
    }
    
    if (parsed <= 0) {
      return 'Amount must be greater than 0';
    }
    
    if (parsed < MIN_WITHDRAWAL_AMOUNT) {
      return `Minimum withdrawal is $${MIN_WITHDRAWAL_AMOUNT}`;
    }
    
    if (parsed > withdrawableBalance) {
      return 'Exceeds withdrawable balance';
    }
    
    return null;
  };

  const handleAmountChange = (e) => {
    const value = e.target.value;
    setAmount(value);
    setAmountError(validateAmount(value));
  };

  const handleSubmit = async () => {
    // Prevent double-submit
    if (isSubmittingRef.current || submitting) {
      return;
    }
    
    // Validation
    const parsedAmount = parseFloat(amount);
    const validationError = validateAmount(amount);
    
    if (validationError) {
      setAmountError(validationError);
      toast.error(validationError);
      return;
    }
    
    if (!method) {
      toast.error('Please select a withdrawal method');
      return;
    }
    
    if (!accountNumber?.trim()) {
      toast.error('Please enter account number');
      return;
    }
    
    if (!accountName?.trim()) {
      toast.error('Please enter account name');
      return;
    }

    // Generate new idempotency key for this submission
    idempotencyKeyRef.current = generateIdempotencyKey();
    
    setSubmitting(true);
    isSubmittingRef.current = true;
    setError(null);
    
    try {
      const response = await http.post('/withdrawal/wallet', {
        amount: parsedAmount,
        withdrawal_method: method.toUpperCase(),
        account_number: accountNumber.trim(),
        account_name: accountName.trim()
      }, withIdempotency(idempotencyKeyRef.current));

      if (response.data.success) {
        setOrderId(response.data.order_id || response.data.withdrawal_id);
        setOrderStatus(response.data.status || 'pending_approval');
        setSuccess(true);
        toast.success('Withdrawal request submitted!');
      } else {
        throw new Error(response.data.message || 'Withdrawal failed');
      }
    } catch (err) {
      // Categorize error type
      const isNetworkErr = isServerUnavailable(err);
      const errResponse = err.response?.data;
      
      let message;
      if (isNetworkErr) {
        message = 'Network error. Please check your connection and try again.';
      } else if (errResponse?.error_code === 'INSUFFICIENT_FUNDS' || errResponse?.message?.toLowerCase().includes('insufficient')) {
        message = 'Insufficient funds. Please check your withdrawable balance.';
      } else if (err.response?.status === 401 || err.response?.status === 403) {
        message = 'Authentication error. Please log in again.';
      } else {
        message = getErrorMessage(err, 'Failed to submit request');
      }
      
      setError(message);
      toast.error(message);
      // Reset idempotency key on error to allow retry
      idempotencyKeyRef.current = null;
    } finally {
      setSubmitting(false);
      isSubmittingRef.current = false;
    }
  };

  if (loading) {
    return <PageLoader message="Loading wallet..." />;
  }

  if (success) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
        <div className="max-w-sm w-full text-center">
          <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Request Submitted!</h2>
          <p className="text-gray-400 mb-4">
            Your withdrawal request for ${toMoney(amount)} has been submitted.
          </p>
          
          {/* Order Details */}
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl mb-4">
            <div className="space-y-2 text-left">
              {orderId && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">Order ID</span>
                  <span className="font-mono text-emerald-400 text-sm">{orderId.slice(0, 12)}...</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Amount</span>
                <span className="text-white font-semibold">${toMoney(amount)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Method</span>
                <span className="text-white capitalize">{method}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Status</span>
                <span className="text-amber-400 text-sm capitalize">{(orderStatus || 'pending').replace(/_/g, ' ')}</span>
              </div>
            </div>
          </div>
          
          {/* Pending approval info */}
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Info className="w-5 h-5 text-amber-400" />
              <p className="text-amber-400 font-medium text-sm">Pending Approval</p>
            </div>
            <p className="text-xs text-amber-400/70">
              Balance has been deducted. If the withdrawal is rejected, it will be automatically refunded.
            </p>
          </div>
          
          {/* Tracking CTA */}
          <button
            onClick={() => navigate('/client/wallet?tab=transactions')}
            className="w-full py-3 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2 mb-3"
            data-testid="track-withdrawal-btn"
          >
            <History className="w-4 h-4" />
            Track in Wallet → Transactions
          </button>
          
          <button
            onClick={() => navigate('/client/wallet')}
            className="w-full py-3 bg-white/5 hover:bg-white/10 text-gray-300 font-medium rounded-xl transition-all"
            data-testid="back-to-wallet-btn"
          >
            Back to Wallet
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="withdraw-page">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
        <div className="px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/client/wallet')}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <h1 className="text-xl font-bold text-white">Withdraw</h1>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto">
        {/* Available Balance */}
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl mb-6">
          <div className="flex items-center gap-2 mb-1">
            <Wallet className="w-4 h-4 text-emerald-400" />
            <p className="text-xs text-emerald-400">Withdrawable Balance</p>
          </div>
          <p className="text-2xl font-bold text-white">${toMoney(withdrawableBalance)}</p>
          <p className="text-xs text-gray-500 mt-1">Only cash balance can be withdrawn</p>
        </div>

        {/* Approval Warning */}
        <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl mb-6">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-5 h-5 text-amber-400" />
            <p className="text-amber-400 font-medium text-sm">Approval Required</p>
          </div>
          <p className="text-xs text-amber-400/70">
            Withdrawals require admin approval. Balance will be deducted immediately and refunded if rejected.
          </p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2].map(s => (
            <div
              key={s}
              className={`w-2.5 h-2.5 rounded-full transition-all ${
                s === step ? 'w-8 bg-violet-500' : s < step ? 'bg-emerald-500' : 'bg-white/10'
              }`}
            />
          ))}
        </div>

        {/* Step 1: Amount & Method */}
        {step === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold text-white mb-2">Withdrawal Details</h2>
              <p className="text-gray-400 text-sm">Enter amount and select method</p>
            </div>

            {/* Amount Input */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Amount</label>
              <div className="relative">
                <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="number"
                  value={amount}
                  onChange={handleAmountChange}
                  placeholder="0.00"
                  min="0"
                  max={withdrawableBalance}
                  step="0.01"
                  disabled={submitting}
                  className={`w-full pl-11 pr-4 py-3.5 text-lg font-bold bg-white/5 border rounded-xl text-white placeholder-gray-600 focus:outline-none focus:ring-2 ${
                    amountError 
                      ? 'border-red-500/50 focus:border-red-500/50 focus:ring-red-500/20' 
                      : 'border-white/10 focus:border-violet-500/50 focus:ring-violet-500/20'
                  }`}
                  data-testid="amount-input"
                />
              </div>
              {amountError && (
                <p className="text-xs text-red-400 mt-2 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {amountError}
                </p>
              )}
              <p className="text-xs text-gray-500 mt-2">
                Min: ${MIN_WITHDRAWAL_AMOUNT} • Max: ${toMoney(withdrawableBalance)}
              </p>
            </div>
            
            {/* Cashout Preview */}
            {previewLoading && (
              <div className="p-3 bg-white/5 rounded-xl flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-violet-400" />
                <span className="text-sm text-gray-400">Calculating payout...</span>
              </div>
            )}
            
            {cashoutPreview && !previewLoading && (
              <div className="p-4 bg-violet-500/10 border border-violet-500/20 rounded-xl space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <Info className="w-4 h-4 text-violet-400" />
                  <span className="text-violet-400 text-xs font-medium">Payout Preview</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400 text-sm">You receive</span>
                  <span className="text-emerald-400 font-bold">
                    ${toMoney(cashoutPreview.net_payout || cashoutPreview.receive_amount || amount)}
                  </span>
                </div>
                {toNumber(cashoutPreview.forfeited_amount || cashoutPreview.bonus_forfeited) > 0 && (
                  <div className="flex items-start gap-2 pt-2 border-t border-white/5">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-amber-400 text-xs">Bonus forfeited:</p>
                      <p className="text-amber-400 font-semibold">
                        ${toMoney(cashoutPreview.forfeited_amount || cashoutPreview.bonus_forfeited)}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {previewError && !previewLoading && amount && parseFloat(amount) > 0 && (
              <div className="p-3 bg-amber-500/10 rounded-xl flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span className="text-xs text-amber-400">{previewError}</span>
              </div>
            )}

            {/* Method Selection */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Withdrawal Method</label>
              <div className="space-y-2">
                {withdrawalMethods.map(m => (
                  <button
                    key={m.id}
                    onClick={() => setMethod(m.id)}
                    disabled={submitting}
                    className={`w-full p-4 rounded-xl border transition-all flex items-center gap-3 ${
                      method === m.id
                        ? 'bg-violet-500/10 border-violet-500/50'
                        : 'bg-white/[0.02] border-white/5 hover:border-white/20'
                    }`}
                    data-testid={`method-${m.id}`}
                  >
                    <Building2 className="w-5 h-5 text-gray-400" />
                    <span className="font-medium text-white">{m.name}</span>
                    {method === m.id && (
                      <CheckCircle className="w-5 h-5 text-violet-400 ml-auto" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => {
                const err = validateAmount(amount);
                if (err) {
                  setAmountError(err);
                  toast.error(err);
                  return;
                }
                if (!method) {
                  toast.error('Please select a withdrawal method');
                  return;
                }
                setStep(2);
              }}
              disabled={!amount || !!amountError || !method || submitting}
              className="w-full py-4 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all"
              data-testid="continue-btn"
            >
              Continue
            </button>
          </div>
        )}

        {/* Step 2: Account Details */}
        {step === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold text-white mb-2">Account Details</h2>
              <p className="text-gray-400 text-sm">Where should we send the funds?</p>
            </div>

            {/* Summary */}
            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-xl">
              <div className="flex justify-between mb-2">
                <span className="text-gray-400">Amount</span>
                <span className="font-bold text-white">${toMoney(amount)}</span>
              </div>
              <div className="flex justify-between mb-2">
                <span className="text-gray-400">Method</span>
                <span className="text-white capitalize">{method}</span>
              </div>
              {cashoutPreview && toNumber(cashoutPreview.net_payout || cashoutPreview.receive_amount) > 0 && (
                <div className="flex justify-between pt-2 border-t border-white/5">
                  <span className="text-gray-400">You receive</span>
                  <span className="text-emerald-400 font-bold">
                    ${toMoney(cashoutPreview.net_payout || cashoutPreview.receive_amount)}
                  </span>
                </div>
              )}
            </div>

            {/* Account Number */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">
                {method === 'bank' ? 'Account Number' : 'Mobile Number'}
              </label>
              <input
                type="text"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder={method === 'bank' ? '1234567890' : '09XX XXX XXXX'}
                disabled={submitting}
                className="w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 disabled:opacity-50"
                data-testid="account-number-input"
              />
            </div>

            {/* Account Name */}
            <div>
              <label className="text-sm text-gray-400 mb-2 block">Account Name</label>
              <input
                type="text"
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
                placeholder="Juan Dela Cruz"
                disabled={submitting}
                className="w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 disabled:opacity-50"
                data-testid="account-name-input"
              />
            </div>

            {/* Error Display */}
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                disabled={submitting}
                className="flex-1 py-4 bg-white/5 hover:bg-white/10 disabled:opacity-50 text-white font-semibold rounded-xl transition-all"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={!accountNumber?.trim() || !accountName?.trim() || submitting}
                className="flex-1 py-4 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                data-testid="submit-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Confirm Withdrawal'
                )}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Withdraw;
