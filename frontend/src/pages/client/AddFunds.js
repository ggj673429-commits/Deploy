/**
 * AddFunds - Production-grade deposit flow
 * Route: /client/wallet/add
 * 
 * Features:
 * - Amount input with quick amounts
 * - Payment method selection (fetched from API with tags/instructions)
 * - Proof upload with size validation
 * - Idempotency for submit
 * - Success state with order ID and tracking CTA
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  Upload, DollarSign, CreditCard, 
  Smartphone, Building2, CheckCircle, Loader2,
  ArrowLeft, Info, AlertCircle, Clock, Tag, FileText, QrCode, History, RefreshCw
} from 'lucide-react';

// Centralized API
import http, { getErrorMessage, isServerUnavailable } from '../../api/http';
import { toMoney } from '../../utils/normalize';
import { generateIdempotencyKey, withIdempotency } from '../../utils/idempotency';

// Constants
const MAX_IMAGE_SIZE_MB = 3;
const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;
const MAX_BASE64_LENGTH = MAX_IMAGE_SIZE_BYTES * 1.37; // base64 inflates ~37%

const getIcon = (iconType) => {
  switch(iconType?.toLowerCase()) {
    case 'smartphone':
    case 'gcash':
    case 'paymaya':
      return Smartphone;
    case 'building':
    case 'bank':
      return Building2;
    case 'card':
      return CreditCard;
    default:
      return CreditCard;
  }
};

/**
 * Normalize QR codes field from API response
 * Handles: qr_codes, qrCodes, qrs
 */
const getQrCodes = (method) => {
  if (!method) return [];
  return method.qr_codes || method.qrCodes || method.qrs || [];
};

const AddFunds = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [loadingMethods, setLoadingMethods] = useState(true);
  const [methodsError, setMethodsError] = useState(null);
  const [proofImage, setProofImage] = useState(null);
  const [proofPreview, setProofPreview] = useState('');
  const [proofError, setProofError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [orderId, setOrderId] = useState(null);
  const [orderStatus, setOrderStatus] = useState(null);
  const [error, setError] = useState(null);
  
  // Idempotency key - generate once per submission attempt
  const idempotencyKeyRef = useRef(null);
  // Prevent double-submit
  const isSubmittingRef = useRef(false);

  const quickAmounts = [20, 50, 100, 200, 500];

  // Fetch payment methods from API
  const fetchPaymentMethods = useCallback(async () => {
    setLoadingMethods(true);
    setMethodsError(null);
    try {
      const response = await http.get('/payments/methods');
      if (response.data.success && response.data.methods?.length > 0) {
        setPaymentMethods(response.data.methods);
      } else {
        // No methods configured
        setPaymentMethods([]);
      }
    } catch (err) {
      console.error('Failed to fetch payment methods:', err);
      const isNetworkErr = isServerUnavailable(err);
      setMethodsError(isNetworkErr ? 'network' : 'api');
      setPaymentMethods([]);
    } finally {
      setLoadingMethods(false);
    }
  }, []);

  useEffect(() => {
    fetchPaymentMethods();
  }, [fetchPaymentMethods]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    setProofError(null);
    
    if (file) {
      // Check file size
      if (file.size > MAX_IMAGE_SIZE_BYTES) {
        setProofError(`Image must be less than ${MAX_IMAGE_SIZE_MB}MB. Your file is ${(file.size / 1024 / 1024).toFixed(1)}MB.`);
        toast.error(`Image too large. Max ${MAX_IMAGE_SIZE_MB}MB allowed.`);
        return;
      }
      
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result;
        
        // Double-check base64 length
        if (base64.length > MAX_BASE64_LENGTH) {
          setProofError(`Image data too large after encoding. Please use a smaller image.`);
          toast.error('Image too large after encoding');
          return;
        }
        
        setProofImage(base64);
        setProofPreview(base64);
      };
      reader.onerror = () => {
        setProofError('Failed to read image file');
        toast.error('Failed to read image file');
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async () => {
    // Prevent double-submit
    if (isSubmittingRef.current || submitting) {
      return;
    }
    
    // Validation
    const parsedAmount = parseFloat(amount);
    if (!amount || !Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    if (!paymentMethod) {
      toast.error('Please select a payment method');
      return;
    }
    // Require method_id
    if (!paymentMethod.method_id) {
      toast.error('Payment method misconfigured. Please select another method or contact support.');
      return;
    }
    if (!proofImage) {
      toast.error('Please upload payment proof');
      return;
    }

    // Generate new idempotency key for this submission
    idempotencyKeyRef.current = generateIdempotencyKey();
    
    setSubmitting(true);
    isSubmittingRef.current = true;
    setError(null);
    
    try {
      const response = await http.post('/wallet-load/request', {
        amount: parsedAmount,
        payment_method: paymentMethod.method_id.toUpperCase(),
        proof_image: proofImage,
        notes: `Via ${paymentMethod.title}`
      }, withIdempotency(idempotencyKeyRef.current));

      if (response.data.success) {
        setOrderId(response.data.order_id || response.data.request_id);
        setOrderStatus(response.data.status || 'pending_review');
        setSuccess(true);
        toast.success('Deposit request submitted!');
      } else {
        throw new Error(response.data.message || 'Submission failed');
      }
    } catch (err) {
      const message = getErrorMessage(err, 'Failed to submit request');
      setError(message);
      toast.error(message);
      // Reset idempotency key on error to allow retry
      idempotencyKeyRef.current = null;
    } finally {
      setSubmitting(false);
      isSubmittingRef.current = false;
    }
  };

  // Get selected method's tags and instructions
  const selectedTags = paymentMethod?.tags || [];
  const selectedInstructions = paymentMethod?.instructions || '';
  const selectedQrCodes = getQrCodes(paymentMethod);
  
  // QR Code state
  const [showQr, setShowQr] = useState(false);
  const [qrData, setQrData] = useState(null);
  const [qrLoading, setQrLoading] = useState(false);

  // Use the selected payment method's QR codes
  const fetchQrCode = async () => {
    setQrLoading(true);
    try {
      const qrCodes = getQrCodes(paymentMethod);
      if (qrCodes.length > 0) {
        const defaultQr = qrCodes.find(q => q.is_default) || qrCodes[0];
        setQrData({
          qr_image: defaultQr.image_url || defaultQr.imageUrl || defaultQr.image,
          account_name: defaultQr.account_name || defaultQr.accountName,
          account_number: defaultQr.account_number || defaultQr.accountNumber,
          label: defaultQr.label
        });
        setShowQr(true);
      } else {
        toast.error('No QR code available for this payment method');
      }
    } catch (err) {
      toast.error(getErrorMessage(err, 'QR code not available'));
    } finally {
      setQrLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
        <div className="max-w-sm w-full text-center">
          <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Request Submitted!</h2>
          <p className="text-gray-400 mb-4">
            Your deposit request for ${toMoney(amount)} has been submitted.
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
                <span className="text-gray-400 text-sm">Status</span>
                <span className="text-amber-400 text-sm capitalize">{(orderStatus || 'pending').replace(/_/g, ' ')}</span>
              </div>
            </div>
          </div>
          
          {/* Approval info */}
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-amber-400" />
              <p className="text-amber-400 font-medium text-sm">Processing Your Request</p>
            </div>
            <p className="text-xs text-amber-400/70">
              Your deposit is in queue for review. This usually takes 2-5 minutes.
            </p>
          </div>

          {/* Tracking CTA */}
          <div className="space-y-3 mb-6">
            <button
              onClick={() => navigate('/client/wallet?tab=deposits')}
              className="w-full py-3 bg-violet-600 hover:bg-violet-500 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
              data-testid="track-deposit-btn"
            >
              <History className="w-4 h-4" />
              Track in Wallet → Deposits
            </button>
            
            {selectedQrCodes.length > 0 && (
              <button
                onClick={fetchQrCode}
                disabled={qrLoading}
                className="w-full py-3 bg-white/10 hover:bg-white/15 text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2"
                data-testid="show-qr-btn"
              >
                {qrLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <QrCode className="w-4 h-4" />
                    Show Payment QR
                  </>
                )}
              </button>
            )}
          </div>

          {/* QR Modal */}
          {showQr && qrData && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={() => setShowQr(false)}>
              <div className="bg-[#12121a] border border-white/10 rounded-2xl p-6 max-w-sm w-full" onClick={(e) => e.stopPropagation()}>
                <h3 className="text-lg font-bold text-white mb-4 text-center">Payment QR Code</h3>
                {qrData.qr_image ? (
                  <img src={qrData.qr_image} alt="Payment QR" className="w-48 h-48 mx-auto rounded-xl bg-white p-2" />
                ) : qrData.qr_data ? (
                  <div className="w-48 h-48 mx-auto bg-white/10 rounded-xl flex items-center justify-center">
                    <p className="text-xs text-gray-400 text-center px-4 break-all">{qrData.qr_data}</p>
                  </div>
                ) : (
                  <div className="w-48 h-48 mx-auto bg-white/5 rounded-xl flex items-center justify-center">
                    <p className="text-gray-500 text-sm">QR not available</p>
                  </div>
                )}
                <p className="text-xs text-gray-400 text-center mt-4">
                  Scan & pay. Deposit will be credited after approval.
                </p>
                <button
                  onClick={() => setShowQr(false)}
                  className="w-full mt-4 py-2 bg-white/10 text-white rounded-xl"
                >
                  Close
                </button>
              </div>
            </div>
          )}
          
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
    <div className="min-h-screen bg-[#0a0a0f]" data-testid="add-funds-page">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-white/5">
        <div className="px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/client/wallet')}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <h1 className="text-xl font-bold text-white">Add Funds</h1>
        </div>
      </header>

      <main className="px-4 py-6 max-w-lg mx-auto">
        {/* Approval Notice */}
        <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl mb-6">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-5 h-5 text-blue-400" />
            <p className="text-blue-400 font-medium text-sm">Requires 2-5 minutes for approval.</p>
          </div>
          <p className="text-xs text-blue-400/70">
            After submitting, your deposit will be on a short queue for review.
          </p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map(s => (
            <div
              key={s}
              className={`w-2.5 h-2.5 rounded-full transition-all ${
                s === step ? 'w-8 bg-violet-500' : s < step ? 'bg-emerald-500' : 'bg-white/10'
              }`}
            />
          ))}
        </div>

        {/* Step 1: Amount */}
        {step === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Enter Amount</h2>
              <p className="text-gray-400">How much would you like to deposit?</p>
            </div>

            {/* Amount Input */}
            <div className="relative">
              <DollarSign className="absolute left-4 top-1/2 -translate-y-1/2 w-6 h-6 text-gray-500" />
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                min="0"
                step="0.01"
                className="w-full pl-12 pr-4 py-4 text-2xl font-bold bg-white/5 border border-white/10 rounded-2xl text-white placeholder-gray-600 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20"
                data-testid="amount-input"
              />
            </div>

            {/* Quick Amount Buttons */}
            <div className="flex flex-wrap gap-2">
              {quickAmounts.map(amt => (
                <button
                  key={amt}
                  onClick={() => setAmount(amt.toString())}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    amount === amt.toString()
                      ? 'bg-violet-500 text-white'
                      : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  ${amt}
                </button>
              ))}
            </div>

            <button
              onClick={() => {
                const parsed = parseFloat(amount);
                if (Number.isFinite(parsed) && parsed > 0) {
                  setStep(2);
                } else {
                  toast.error('Please enter a valid amount');
                }
              }}
              disabled={!amount || parseFloat(amount) <= 0}
              className="w-full py-4 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all"
              data-testid="continue-btn"
            >
              Continue
            </button>
          </div>
        )}

        {/* Step 2: Payment Method */}
        {step === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Payment Method</h2>
              <p className="text-gray-400">Select how you'll pay</p>
            </div>

            {loadingMethods ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
              </div>
            ) : methodsError ? (
              /* Error State - differentiate network vs API error */
              <div className="p-8 bg-white/[0.02] border border-white/5 rounded-2xl text-center" data-testid="methods-error">
                <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">
                  {methodsError === 'network' ? 'Connection Error' : 'Failed to Load'}
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  {methodsError === 'network' 
                    ? 'Unable to connect to server. Please check your internet connection.'
                    : 'Failed to load payment methods. Please try again.'}
                </p>
                <button
                  onClick={fetchPaymentMethods}
                  className="px-6 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-xl transition-all flex items-center gap-2 mx-auto"
                  data-testid="retry-methods-btn"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </button>
              </div>
            ) : paymentMethods.length === 0 ? (
              /* Empty State - No payment methods configured */
              <div className="p-8 bg-white/[0.02] border border-white/5 rounded-2xl text-center" data-testid="no-payment-methods">
                <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">No Payment Methods Available</h3>
                <p className="text-gray-400 text-sm mb-4">
                  Payment methods are not configured yet. Please contact support.
                </p>
                <button
                  onClick={() => navigate('/client/wallet')}
                  className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl transition-all"
                >
                  Back to Wallet
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {paymentMethods.map(method => {
                  const Icon = getIcon(method.icon || method.method_id);
                  const isSelected = paymentMethod?.method_id === method.method_id;
                  const qrCodes = getQrCodes(method);
                  const hasQrCodes = qrCodes.length > 0;
                  const isMisconfigured = !method.method_id;
                  
                  return (
                    <button
                      key={method.method_id || method.title}
                      onClick={() => !isMisconfigured && setPaymentMethod(method)}
                      disabled={isMisconfigured}
                      className={`w-full p-4 rounded-2xl border transition-all text-left ${
                        isMisconfigured
                          ? 'bg-red-500/5 border-red-500/20 opacity-50 cursor-not-allowed'
                          : isSelected
                          ? 'bg-violet-500/10 border-violet-500/50'
                          : 'bg-white/[0.02] border-white/5 hover:border-white/20'
                      }`}
                      data-testid={`method-${method.method_id || 'unknown'}`}
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-violet-500/10 flex items-center justify-center">
                          <Icon className="w-6 h-6 text-violet-400" />
                        </div>
                        <div className="flex-1">
                          <span className="font-medium text-white">{method.title}</span>
                          {isMisconfigured && (
                            <p className="text-xs text-red-400 mt-0.5">Misconfigured</p>
                          )}
                          {method.tags?.length > 0 && !isMisconfigured && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {method.tags.slice(0, 2).map((tag, i) => (
                                <span key={i} className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                          {hasQrCodes && !isMisconfigured && (
                            <div className="flex items-center gap-1 mt-1">
                              <QrCode className="w-3 h-3 text-emerald-400" />
                              <span className="text-[10px] text-emerald-400">QR Available</span>
                            </div>
                          )}
                        </div>
                        {isSelected && !isMisconfigured && (
                          <CheckCircle className="w-5 h-5 text-violet-400" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {paymentMethods.length > 0 && !methodsError && (
              <div className="flex gap-3">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 py-4 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl transition-all"
                >
                  Back
                </button>
                <button
                  onClick={() => {
                    if (paymentMethod && paymentMethod.method_id) {
                      setStep(3);
                    } else if (paymentMethod && !paymentMethod.method_id) {
                      toast.error('Selected payment method is misconfigured');
                    } else {
                      toast.error('Please select a payment method');
                    }
                  }}
                  disabled={!paymentMethod || !paymentMethod.method_id}
                  className="flex-1 py-4 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all"
                >
                  Continue
                </button>
              </div>
            )}
          </div>
        )}

        {/* Step 3: Upload Proof */}
        {step === 3 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Upload Proof</h2>
              <p className="text-gray-400">Upload screenshot of your payment</p>
            </div>

            {/* Summary */}
            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Amount</span>
                <span className="font-bold text-white">${toMoney(amount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Method</span>
                <span className="text-white">{paymentMethod?.title}</span>
              </div>
              
              {/* Payment Tag - Account to pay to */}
              {selectedTags.length > 0 && (
                <div className="pt-3 border-t border-white/5">
                  <div className="flex items-center gap-2 mb-2">
                    <Tag className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400 text-xs font-medium">Payment Tag</span>
                  </div>
                  <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3">
                    <p className="text-emerald-300 font-mono font-semibold text-base">
                      {selectedTags[0]}
                    </p>
                    {selectedTags.length > 1 && (
                      <p className="text-emerald-400/60 text-xs mt-1">
                        Alt: {selectedTags.slice(1).join(', ')}
                      </p>
                    )}
                  </div>
                </div>
              )}
              
              {/* Note - What to write in remarks */}
              {selectedInstructions && (
                <div className="pt-3 border-t border-white/5">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-4 h-4 text-amber-400" />
                    <span className="text-amber-400 text-xs font-medium">Note</span>
                  </div>
                  <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
                    <p className="text-amber-300 text-sm">
                      Please write <span className="font-mono font-semibold">"{selectedInstructions}"</span> in remarks
                    </p>
                  </div>
                </div>
              )}
              
              {/* Deposit QR Codes from backend payment method */}
              {selectedQrCodes.length > 0 && (
                <div className="pt-3 border-t border-white/5">
                  <div className="flex items-center gap-2 mb-3">
                    <QrCode className="w-4 h-4 text-violet-400" />
                    <span className="text-violet-400 text-xs font-medium">Payment QR Code</span>
                  </div>
                  <div className="space-y-3">
                    {selectedQrCodes.map((qr, idx) => {
                      const qrImage = qr.image_url || qr.imageUrl || qr.image;
                      const qrAccountName = qr.account_name || qr.accountName;
                      const qrAccountNumber = qr.account_number || qr.accountNumber;
                      return (
                      <div 
                        key={qr.qr_id || idx} 
                        className={`bg-violet-500/10 border ${qr.is_default ? 'border-violet-500/50' : 'border-violet-500/20'} rounded-xl p-3`}
                        data-testid={`deposit-qr-${qr.qr_id || idx}`}
                      >
                        {qr.is_default && (
                          <span className="text-[10px] px-2 py-0.5 bg-violet-500/30 text-violet-300 rounded-full mb-2 inline-block">
                            Primary
                          </span>
                        )}
                        {qr.label && (
                          <p className="text-white font-medium text-sm mb-1">{qr.label}</p>
                        )}
                        {qrAccountName && (
                          <p className="text-gray-400 text-xs mb-1">Account: {qrAccountName}</p>
                        )}
                        {qrAccountNumber && (
                          <p className="text-emerald-400 font-mono text-sm mb-2">{qrAccountNumber}</p>
                        )}
                        {qrImage && (
                          <div className="mt-2">
                            <img 
                              src={qrImage} 
                              alt={qr.label || 'Payment QR'} 
                              className="w-40 h-40 mx-auto rounded-lg bg-white p-1"
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          </div>
                        )}
                      </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Upload Area */}
            <div className="relative">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                data-testid="proof-upload"
                disabled={submitting}
              />
              <div className={`p-8 border-2 border-dashed rounded-2xl text-center transition-all ${
                proofError
                  ? 'border-red-500/50 bg-red-500/5'
                  : proofPreview 
                  ? 'border-emerald-500/50 bg-emerald-500/5' 
                  : 'border-white/10 hover:border-white/30'
              }`}>
                {proofPreview ? (
                  <div className="space-y-4">
                    <img 
                      src={proofPreview} 
                      alt="Payment proof" 
                      className="max-h-40 mx-auto rounded-xl"
                    />
                    <p className="text-emerald-400 text-sm">Image uploaded ✓</p>
                    <p className="text-xs text-gray-500">Tap to change</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Upload className="w-10 h-10 text-gray-500 mx-auto" />
                    <p className="text-gray-400">Tap to upload payment screenshot</p>
                    <p className="text-xs text-gray-600">PNG, JPG up to {MAX_IMAGE_SIZE_MB}MB</p>
                  </div>
                )}
              </div>
            </div>
            
            {/* Proof Error */}
            {proofError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                <p className="text-red-400 text-sm">{proofError}</p>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep(2)}
                disabled={submitting}
                className="flex-1 py-4 bg-white/5 hover:bg-white/10 disabled:opacity-50 text-white font-semibold rounded-xl transition-all"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={!proofImage || submitting || !!proofError}
                className="flex-1 py-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
                data-testid="submit-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  'Submit Request'
                )}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default AddFunds;
