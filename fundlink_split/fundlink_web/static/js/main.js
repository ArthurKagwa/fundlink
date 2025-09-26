// FundLink - Main JavaScript

/**
 * Global utilities and common functionality
 */
class FundLinkUtils {
    /**
     * Format numbers with proper decimals
     */
    static formatNumber(num, decimals = 4) {
        return parseFloat(num).toFixed(decimals).replace(/\.?0+$/, '');
    }

    /**
     * Format wallet address for display
     */
    static formatAddress(address, length = 8) {
        if (!address || address.length < 10) return address;
        return `${address.slice(0, length)}...${address.slice(-4)}`;
    }

    /**
     * Validate Ethereum address format
     */
    static isValidAddress(address) {
        return /^0x[a-fA-F0-9]{40}$/.test(address);
    }

    /**
     * Copy text to clipboard
     */
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Copied to clipboard!', 'success');
            return true;
        } catch (err) {
            console.error('Failed to copy:', err);
            this.showToast('Failed to copy', 'error');
            return false;
        }
    }

    /**
     * Show toast notification
     */
    static showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        const bgColor = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        }[type] || '#17a2b8';

        toast.className = 'toast-notification';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${bgColor};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-weight: 500;
        `;

        document.body.appendChild(toast);
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, duration);
    }

    /**
     * Format date for display
     */
    static formatDate(dateString, includeTime = true) {
        const date = new Date(dateString);
        const options = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        };

        if (includeTime) {
            options.hour = '2-digit';
            options.minute = '2-digit';
        }

        return date.toLocaleDateString('en-US', options);
    }

    /**
     * Debounce function calls
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Generate MetaMask deep link for donations
     */
    static generateMetaMaskLink(recipientAddress, amount, token = 'AVAX') {
        if (!this.isValidAddress(recipientAddress)) {
            throw new Error('Invalid recipient address');
        }

        const chainId = '43113';
        const base = `https://link.metamask.io/send/${recipientAddress}@${chainId}`;

        if (token === 'AVAX') {
            // Convert AVAX to wei (18 decimals)
            const amountWei = (parseFloat(amount) * Math.pow(10, 18)).toString();
            return `${base}?value=${amountWei}`;
        } else if (token === 'USDT') {
            // USDT has 6 decimals
            const amountUSDT = (parseFloat(amount) * Math.pow(10, 6)).toString();
            const usdtContract = '0x5425890298aed601595a70AB815c96711a31Bc65';
            return `${base}?asset=${usdtContract}&value=${amountUSDT}`;
        } else {
            throw new Error('Unsupported token');
        }
    }

    /**
     * Get Snowtrace explorer URL for transaction
     */
    static getExplorerUrl(txHash) {
        return `https://testnet.snowtrace.io/tx/${txHash}`;
    }
}

/**
 * API Service for backend communication
 */
class APIService {
    constructor() {
        this.baseURL = '/api';
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
        this.debug = (window.FUNDLINK_DEBUG === true) || (localStorage.getItem('fundlink_debug') === '1');
    }

    /**
     * Make API request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };
        const started = performance.now ? performance.now() : Date.now();
        try {
            const response = await fetch(url, config);
            const durationMs = (performance.now ? performance.now() : Date.now()) - started;

            if (!response.ok) {
                let parsed = null;
                let textBody = '';
                try { parsed = await response.json(); } catch (e) {
                    try { textBody = await response.text(); } catch (_) { textBody = ''; }
                }
                const correlationId = (crypto && crypto.randomUUID) ? crypto.randomUUID() : `cid_${Date.now()}_${Math.random().toString(16).slice(2)}`;
                const message = this._deriveErrorMessage(parsed, response.status) || `HTTP ${response.status}`;
                const apiError = new Error(message);
                apiError.name = 'APIError';
                apiError.status = response.status;
                apiError.data = parsed;
                apiError.rawBody = textBody;
                apiError.endpoint = endpoint;
                apiError.method = config.method || 'GET';
                apiError.durationMs = Math.round(durationMs);
                apiError.correlationId = correlationId;
                if (this.debug || response.status >= 400) {
                    if (console.groupCollapsed) {
                        console.groupCollapsed(`[API ERROR] ${apiError.method} ${url} ${response.status} (${apiError.correlationId})`);
                        console.error('Message:', message);
                        console.error('Status:', response.status);
                        console.error('Endpoint:', endpoint);
                        console.error('Duration(ms):', apiError.durationMs);
                        console.error('Data:', parsed);
                        if (textBody && !parsed) console.error('Raw Body:', textBody);
                        console.error('Request Headers:', config.headers);
                        if (config.body) console.error('Request Body:', this._safeJsonParse(config.body));
                        console.groupEnd();
                    } else {
                        console.error('[API ERROR]', apiError);
                    }
                }
                window.dispatchEvent(new CustomEvent('fundlink:apiError', { detail: apiError }));
                throw apiError;
            }
            const json = await response.json();
            return json;
        } catch (error) {
            if (!(error instanceof Error)) {
                const wrap = new Error('Unknown network error');
                wrap.original = error;
                error = wrap;
            }
            if (this.debug) console.error('API Request failed (network/runtime):', { endpoint, error });
            window.dispatchEvent(new CustomEvent('fundlink:apiNetworkError', { detail: error }));
            throw error;
        }
    }

    _safeJsonParse(body) {
        try { return JSON.parse(body); } catch (_) { return body; }
    }

    _deriveErrorMessage(data, status) {
        if (!data) return '';
        if (typeof data === 'string') return data;
        if (data.message) return data.message;
        if (data.detail) return data.detail;
        const keys = Object.keys(data);
        if (!keys.length) return '';
        const parts = [];
        for (const k of keys.slice(0, 4)) {
            const v = data[k];
            if (Array.isArray(v)) parts.push(`${k}: ${v[0]}`);
            else if (typeof v === 'string') parts.push(`${k}: ${v}`);
        }
        if (keys.length > 4) parts.push('...');
        return parts.join(' | ') || `HTTP ${status}`;
    }

    /**
     * Get campaigns
     */
    async getCampaigns(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/campaigns/?${queryString}`);
    }

    /**
     * Get campaign details
     */
    async getCampaign(id) {
        return this.request(`/campaigns/${id}/`);
    }

    /**
     * Get campaign statistics
     */
    async getCampaignStats(id) {
        return this.request(`/campaigns/${id}/stats/`);
    }

    /**
     * Get donations
     */
    async getDonations(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/donations/?${queryString}`);
    }

    /**
     * Submit NGO application
     */
    async submitNGOApplication(data) {
        return this.request('/ngos/apply/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
}

/**
 * Wallet integration utilities
 */
class WalletIntegration {
    constructor() {
        this.isMetaMaskInstalled = this.checkMetaMaskInstalled();
    }

    checkMetaMaskInstalled() {
        return typeof window.ethereum !== 'undefined';
    }

    /**
     * Connect to MetaMask
     */
    async connectMetaMask() {
        if (!this.isMetaMaskInstalled) {
            FundLinkUtils.showToast('MetaMask is not installed', 'error');
            return null;
        }

        try {
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });
            
            if (accounts.length > 0) {
                FundLinkUtils.showToast('Wallet connected!', 'success');
                return accounts[0];
            }
        } catch (error) {
            console.error('MetaMask connection failed:', error);
            FundLinkUtils.showToast('Failed to connect wallet', 'error');
        }
        
        return null;
    }

    /**
     * Switch to Avalanche Fuji network
     */
    async switchToFuji() {
        if (!this.isMetaMaskInstalled) return false;

        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: '0xA869' }], // 43113 in hex
            });
            return true;
        } catch (switchError) {
            // Chain not added yet, try to add it
            if (switchError.code === 4902) {
                return this.addFujiNetwork();
            }
            console.error('Failed to switch network:', switchError);
            return false;
        }
    }

    /**
     * Add Avalanche Fuji network to MetaMask
     */
    async addFujiNetwork() {
        try {
            await window.ethereum.request({
                method: 'wallet_addEthereumChain',
                params: [{
                    chainId: '0xA869',
                    chainName: 'Avalanche Fuji Testnet',
                    nativeCurrency: {
                        name: 'AVAX',
                        symbol: 'AVAX',
                        decimals: 18
                    },
                    rpcUrls: ['https://api.avax-test.network/ext/bc/C/rpc'],
                    blockExplorerUrls: ['https://testnet.snowtrace.io/']
                }]
            });
            FundLinkUtils.showToast('Fuji network added!', 'success');
            return true;
        } catch (error) {
            console.error('Failed to add network:', error);
            FundLinkUtils.showToast('Failed to add network', 'error');
            return false;
        }
    }
}

/**
 * Global application state
 */
class AppState {
    constructor() {
        this.data = {
            campaigns: [],
            currentCampaign: null,
            user: null,
            wallet: null
        };
        this.listeners = {};
    }

    set(key, value) {
        this.data[key] = value;
        this.notify(key, value);
    }

    get(key) {
        return this.data[key];
    }

    subscribe(key, callback) {
        if (!this.listeners[key]) {
            this.listeners[key] = [];
        }
        this.listeners[key].push(callback);
    }

    notify(key, value) {
        if (this.listeners[key]) {
            this.listeners[key].forEach(callback => callback(value));
        }
    }
}

// Initialize global instances
const fundLinkUtils = FundLinkUtils;
const apiService = new APIService();
const walletIntegration = new WalletIntegration();
const appState = new AppState();

// Export to global scope
window.FundLinkUtils = FundLinkUtils;
window.apiService = apiService;
window.walletIntegration = walletIntegration;
window.appState = appState;

/**
 * Initialize application
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap is available
    if (window.bootstrap) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Add click handlers for common actions
    document.addEventListener('click', function(e) {
        // Copy wallet address
        if (e.target.matches('.copy-address')) {
            e.preventDefault();
            const address = e.target.dataset.address;
            if (address) {
                FundLinkUtils.copyToClipboard(address);
            }
        }

        // External links
        if (e.target.matches('a[href^="http"]:not([target])')) {
            e.target.target = '_blank';
            e.target.rel = 'noopener noreferrer';
        }
    });

    // Initialize network check if MetaMask is available
    if (walletIntegration.isMetaMaskInstalled) {
        checkNetwork();
    }
});

/**
 * Check if user is on correct network
 */
async function checkNetwork() {
    try {
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        if (chainId !== '0xA869') { // Not on Fuji
            showNetworkWarning();
        }
    } catch (error) {
        console.error('Network check failed:', error);
    }
}

/**
 * Show network warning
 */
function showNetworkWarning() {
    const warning = document.createElement('div');
    warning.className = 'alert alert-warning alert-dismissible fade show';
    warning.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; z-index: 9999; margin: 0; border-radius: 0;';
    warning.innerHTML = `
        <div class="container">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Wrong Network:</strong> Switch to Avalanche Fuji testnet for donations.
            <button type="button" class="btn btn-sm btn-outline-warning ms-2" onclick="walletIntegration.switchToFuji()">
                Switch Network
            </button>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    document.body.insertBefore(warning, document.body.firstChild);
}

/**
 * Enhanced form validation
 */
class FormValidator {
    constructor(form) {
        this.form = form;
        this.rules = {};
        this.init();
    }

    init() {
        this.form.addEventListener('submit', (e) => {
            if (!this.validate()) {
                e.preventDefault();
            }
        });

        // Real-time validation
        this.form.querySelectorAll('input, textarea, select').forEach(field => {
            field.addEventListener('blur', () => this.validateField(field));
        });
    }

    addRule(fieldName, validator, message) {
        if (!this.rules[fieldName]) {
            this.rules[fieldName] = [];
        }
        this.rules[fieldName].push({ validator, message });
    }

    validateField(field) {
        const rules = this.rules[field.name];
        if (!rules) return true;

        for (const rule of rules) {
            if (!rule.validator(field.value)) {
                this.showFieldError(field, rule.message);
                return false;
            }
        }

        this.clearFieldError(field);
        return true;
    }

    validate() {
        let isValid = true;
        
        Object.keys(this.rules).forEach(fieldName => {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (field && !this.validateField(field)) {
                isValid = false;
            }
        });

        return isValid;
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.appendChild(feedback);
        }
        feedback.textContent = message;
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
    }
}

// Make FormValidator available globally
window.FormValidator = FormValidator;

// Global API error listeners for user feedback & lightweight diagnostics
window.addEventListener('fundlink:apiError', (e) => {
    const err = e.detail || {};
    const msg = err.message || 'Request failed';
    const suffix = err.correlationId ? ` (#${err.correlationId.slice(0,8)})` : '';
    FundLinkUtils.showToast(`${msg}${suffix}`, 'error', 5000);
});

window.addEventListener('fundlink:apiNetworkError', (e) => {
    FundLinkUtils.showToast('Network error - please retry', 'error', 4000);
});
