// Nova Billing Demo - One-page UI
// Frontend is intentionally thin. All Metronome calls happen on the server.
// This file only wires buttons to our API and renders results.

// Stable tier taxonomy used across UI (keep in sync with server config)
const TIERS = ['standard', 'high-res', 'ultra'];

// Simple UI state
let isLoading = false; // prevents duplicate generate clicks
let hasCustomer = false; // gates the contract button

document.addEventListener('DOMContentLoaded', () => {
  // Bind button handlers and prime UI
  wireHandlers();
  refreshStatus();
  // Try to load usage if available; fall back gracefully
  loadUsage();
  setInterval(loadUsage, 30000);
});

function wireHandlers() {
  // Button: create customer
  const createBtn = document.getElementById('createCustomerBtn');
  if (createBtn) createBtn.addEventListener('click', handleCreateCustomer);

  // Button: create contract
  const contractBtn = document.getElementById('createContractBtn');
  if (contractBtn) contractBtn.addEventListener('click', handleCreateContract);

  // Buttons: generate usage per tier
  document.querySelectorAll('.generate-btn').forEach(btn => {
    btn.addEventListener('click', handleGenerate);
  });
}

async function refreshStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const s = await res.json();
    // Enable generate buttons when a contract exists
    document.querySelectorAll('.generate-btn').forEach(btn => {
      btn.disabled = !s.contract_id;
    });
    // Disable contract creation until both a customer and a rate card exist
    hasCustomer = !!s.customer_id && !!s.rate_card_id;
    const contractBtn = document.getElementById('createContractBtn');
    if (contractBtn) contractBtn.disabled = !hasCustomer;
    // Show pricing hint only when rate card is missing (uses .hidden CSS util)
    const contractHint = document.getElementById('contractHint');
    if (contractHint) {
      if (s.rate_card_id) contractHint.classList.add('hidden');
      else contractHint.classList.remove('hidden');
    }
  } catch {}
}


async function handleCreateCustomer() {
  // If a customer already existed, show a different toast message after success
  const hadCustomer = hasCustomer;
  const btn = document.getElementById('createCustomerBtn');
  const name = (document.getElementById('customerNameInput')?.value || '').trim();
  const ingestAlias = (document.getElementById('ingestAliasInput')?.value || '').trim();
  try {
    if (btn) btn.disabled = true;
    const payload = ingestAlias ? { name, ingest_alias: ingestAlias } : { name };
    const res = await fetch('/api/customers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || 'Failed to create customer');
    showSuccess(hadCustomer ? 'Customer ready' : 'Customer created');
    // Reset the usage panel for a clean slate with the new customer
    updateUsageDisplay({});
  } catch (e) {
    alert(e.message || 'Failed to create customer');
  } finally {
    if (btn) btn.disabled = false;
    refreshStatus();
  }
}

async function handleCreateContract() {
  // Double-guard: do nothing if customer not present
  if (!hasCustomer) {
    return;
  }
  try {
    const btn = document.getElementById('createContractBtn');
    if (btn) btn.disabled = true;
    const res = await fetch('/api/contract', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || 'Failed to create contract');
    // Contract created -> enable generate buttons immediately
    document.querySelectorAll('.generate-btn').forEach(btn => { btn.disabled = false; });
    showSuccess('Contract created');
  } catch (e) {
    alert(e.message || 'Failed to create contract');
  } finally {
    const btn = document.getElementById('createContractBtn');
    if (btn) btn.disabled = false;
    refreshStatus();
  }
}

async function handleGenerate(evt) {
  if (isLoading) return;
  const btn = evt.currentTarget;
  const tier = btn.dataset.tier;
  const original = btn.textContent;

  isLoading = true;
  // Visually disable all generate buttons during a request
  document.querySelectorAll('.generate-btn').forEach(b => { b.disabled = true; });
  btn.disabled = true;
  btn.innerHTML = `${original}<span class="loading"></span>`;

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // Server generates a deterministic transaction_id by default
      body: JSON.stringify({ tier })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || 'Generation failed');
    showSuccess('Image generated');
    // Ask for updated usage with a simple backoff to account for eventual consistency
    setTimeout(loadUsage, 800);
    setTimeout(loadUsage, 2500);
    setTimeout(loadUsage, 5000);
  } catch (e) {
    alert(e.message || 'Failed to generate');
  } finally {
    isLoading = false;
    // Re-enable generate buttons after request completes
    document.querySelectorAll('.generate-btn').forEach(b => { b.disabled = false; });
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

async function loadUsage() {
  try {
    const res = await fetch('/api/usage');
    if (!res.ok) return;
    const usage = await res.json();
    updateUsageDisplay(usage);
  } catch {}
}


function updateUsageDisplay(usage) {
  let total = 0;
  TIERS.forEach(t => {
    const data = usage?.[t] || { count: 0, amount: 0 };
    const countEl = document.getElementById(`${t}Count`);
    const amountEl = document.getElementById(`${t}Amount`);
    // Count is images generated today; amount is computed server-side
    if (countEl) countEl.textContent = `${data.count} image${data.count === 1 ? '' : 's'}`;
    if (amountEl) amountEl.textContent = `$${Number(data.amount || 0).toFixed(2)}`;
    total += Number(data.amount || 0);
  });
  const totalEl = document.getElementById('totalAmount');
  if (totalEl) totalEl.textContent = `$${total.toFixed(2)}`;
}

function showSuccess(msg) {
  const el = document.getElementById('successMessage');
  if (!el) return;
  el.textContent = msg || 'Success';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}
