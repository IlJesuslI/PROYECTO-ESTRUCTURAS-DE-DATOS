'use strict';

const state = { products: [], pending: [], history: [] };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const money = (value) => new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(value);

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  let payload;
  try { payload = await response.json(); } catch { throw new Error('El servidor devolvió una respuesta inválida.'); }
  if (!response.ok || payload.ok === false) throw new Error(payload.error || `Error HTTP ${response.status}`);
  return payload.data;
}

function showToast(message, type = 'ok') {
  const toast = $('#toast');
  toast.textContent = message;
  toast.className = `toast show${type === 'error' ? ' error' : ''}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = 'toast'; }, 3000);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function priorityLabel(priority) {
  return priority === 2 ? 'Urgente' : priority === 1 ? 'Alta' : 'Normal';
}

function renderProductPicker() {
  const root = $('#orderProducts');
  root.replaceChildren();
  if (!state.products.length) {
    root.append(el('p', 'hint', 'No hay productos activos. Agrega uno en la pestaña Menú.'));
    return;
  }
  state.products.forEach((product) => {
    const row = el('div', 'product-row');
    const meta = el('div', 'meta');
    meta.append(el('strong', '', product.name), el('small', '', money(product.price_cop)));
    const input = el('input', 'qty');
    input.type = 'number'; input.min = '0'; input.max = '99'; input.step = '1'; input.value = '0';
    input.dataset.productId = product.id;
    input.dataset.price = String(product.price_cop);
    input.setAttribute('aria-label', `Cantidad de ${product.name}`);
    input.addEventListener('input', updateOrderTotal);
    row.append(meta, input);
    root.append(row);
  });
  updateOrderTotal();
}

function updateOrderTotal() {
  let total = 0;
  $$('#orderProducts input').forEach((input) => {
    const qty = Number.parseInt(input.value || '0', 10);
    if (Number.isInteger(qty) && qty > 0) total += qty * Number(input.dataset.price);
  });
  $('#orderTotal').textContent = money(total);
}

function renderMenu() {
  const root = $('#menuList');
  root.replaceChildren();
  state.products.forEach((product) => {
    const row = el('div', 'menu-item');
    const meta = el('div', 'meta');
    meta.append(el('strong', '', product.name), el('small', '', money(product.price_cop)));
    const button = el('button', 'danger', 'Desactivar');
    button.addEventListener('click', async () => {
      if (!confirm(`¿Desactivar "${product.name}"? Los pedidos históricos se conservarán.`)) return;
      try {
        await api(`/api/products/${product.id}`, { method: 'DELETE' });
        showToast('Producto desactivado.');
        await refreshAll();
      } catch (error) { showToast(error.message, 'error'); }
    });
    row.append(meta, button); root.append(row);
  });
}

function orderCard(order, canCancel = false) {
  const card = el('article', 'order-card');
  const top = el('div', 'order-top');
  const title = el('div');
  title.append(el('div', 'order-code', `${order.code} · ${order.customer}`), el('div', 'order-meta', new Date(order.created_at).toLocaleString('es-CO')));
  const badge = el('span', `priority p${order.priority}`, priorityLabel(order.priority));
  top.append(title, badge);

  const list = el('ul', 'order-items');
  order.items.forEach((item) => list.append(el('li', '', `${item.quantity} × ${item.name} — ${money(item.subtotal_cop)}`)));

  const bottom = el('div', 'order-bottom');
  bottom.append(el('strong', '', money(order.total_cop)));
  if (canCancel) {
    const cancel = el('button', 'danger', 'Cancelar');
    cancel.addEventListener('click', async () => {
      try {
        await api(`/api/orders/${order.id}/cancel`, { method: 'POST', body: '{}' });
        showToast(`${order.code} cancelado.`); await refreshAll();
      } catch (error) { showToast(error.message, 'error'); }
    });
    bottom.append(cancel);
  }
  card.append(top, list, bottom);
  return card;
}

function renderPending() {
  const root = $('#pendingOrders'); root.replaceChildren();
  state.pending.forEach((order) => root.append(orderCard(order, true)));
}

function renderHistory() {
  const root = $('#historyList'); root.replaceChildren();
  state.history.forEach((order) => root.append(orderCard(order, false)));
}

async function refreshAll() {
  try {
    const [status, products, pending, history] = await Promise.all([
      api('/api/status'), api('/api/products'), api('/api/orders/pending'), api('/api/history?limit=50')
    ]);
    state.products = products; state.pending = pending; state.history = history;
    $('#mProducts').textContent = status.products_active;
    $('#mPending').textContent = status.orders_pending;
    $('#mPrepared').textContent = status.orders_prepared;
    $('#mPriority').textContent = status.priority_queue_size;
    $('#connectionStatus').textContent = 'Servidor conectado';
    renderProductPicker(); renderMenu(); renderPending(); renderHistory();
  } catch (error) {
    $('#connectionStatus').textContent = 'Sin conexión';
    showToast(error.message, 'error');
  }
}

$('#productForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await api('/api/products', {
      method: 'POST',
      body: JSON.stringify({ name: $('#productName').value, price_cop: $('#productPrice').value })
    });
    event.target.reset(); showToast('Producto agregado.'); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});

$('#orderForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const items = $$('#orderProducts input')
    .map((input) => ({ product_id: input.dataset.productId, quantity: Number.parseInt(input.value || '0', 10) }))
    .filter((item) => item.quantity > 0);
  try {
    const order = await api('/api/orders', {
      method: 'POST',
      body: JSON.stringify({ customer: $('#customer').value, priority: Number($('#priority').value), items })
    });
    event.target.reset(); showToast(`${order.code} agregado a la cola.`); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});

$('#processNext').addEventListener('click', async () => {
  try {
    const order = await api('/api/orders/process-next', { method: 'POST', body: '{}' });
    showToast(`${order.code} marcado como preparado.`); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});

$('#undoPrepared').addEventListener('click', async () => {
  try {
    const order = await api('/api/history/undo', { method: 'POST', body: '{}' });
    showToast(`${order.code} regresó a pendientes.`); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});

$$('.tab').forEach((button) => button.addEventListener('click', () => {
  $$('.tab').forEach((tab) => tab.classList.remove('active'));
  $$('.tab-panel').forEach((panel) => panel.classList.remove('active'));
  button.classList.add('active');
  document.getElementById(button.dataset.tab).classList.add('active');
}));

refreshAll();
