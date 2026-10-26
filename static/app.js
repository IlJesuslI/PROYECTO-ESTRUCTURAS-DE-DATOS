'use strict';

const state = { products: [], pending: [], history: [], stats: {}, historyOffset: 0, historyLimit: 30 };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const money = (value) => new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', maximumFractionDigits: 0
}).format(value);

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
  });
  let payload;
  try { payload = await response.json(); }
  catch { throw new Error('El servidor devolvió una respuesta inesperada.'); }
  if (!response.ok || payload.ok === false) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload.data;
}
function el(tag, className = '', text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function showToast(message, type = 'ok') {
  const root = $('#toast');
  root.textContent = message;
  root.className = `toast show${type === 'error' ? ' error' : ''}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { root.className = 'toast'; }, 3400);
}
function friendlyDate(dateText) {
  const date = new Date(dateText);
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : date.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' });
}
function emptyState(title, subtitle) {
  const root = el('div', 'empty-panel');
  root.append(el('div', 'empty-symbol', '◌'), el('strong', '', title), el('p', '', subtitle));
  return root;
}
function productPicker() {
  const root = $('#orderProducts'); root.replaceChildren();
  if (!state.products.length) {
    root.append(emptyState('Sin productos', 'Agrega productos desde Menú para comenzar.'));
    return;
  }
  for (const product of state.products) {
    const row = el('div', 'product-row');
    const icon = el('div', 'product-avatar', '✦');
    const meta = el('div', 'product-meta');
    meta.append(el('strong', '', product.name), el('small', '', money(product.price_cop)));
    const count = el('input', 'qty');
    count.type = 'number'; count.min = '0'; count.max = '99'; count.step = '1'; count.value = '0';
    count.dataset.productId = product.id; count.dataset.price = String(product.price_cop);
    count.setAttribute('aria-label', `Cantidad de ${product.name}`);
    count.addEventListener('input', updateTotal);
    row.append(icon, meta, count); root.append(row);
  }
  updateTotal();
}
function updateTotal() {
  let total = 0;
  for (const input of $$('#orderProducts .qty')) {
    const qty = Number(input.value);
    if (Number.isInteger(qty) && qty >= 1 && qty <= 99) total += qty * Number(input.dataset.price);
  }
  $('#orderTotal').textContent = money(total);
}
function menuList() {
  const root = $('#menuList'); root.replaceChildren();
  if (!state.products.length) {
    root.append(emptyState('El menú está vacío', 'Crea tu primer producto para empezar.'));
    return;
  }
  for (const product of state.products) {
    const card = el('div', 'menu-item');
    const meta = el('div', 'menu-item-main');
    meta.append(el('div', 'menu-icon', '✦'));
    const labels = el('div', 'product-meta');
    labels.append(el('strong', '', product.name), el('small', '', money(product.price_cop)));
    meta.append(labels);
    const actions = el('div', 'menu-actions');
    const edit = el('button', 'btn btn-outline btn-small', 'Editar');
    edit.type = 'button';
    edit.addEventListener('click', async () => {
      const name = prompt('Nombre del producto:', product.name);
      if (name === null) return;
      const price = prompt('Precio en COP:', String(product.price_cop));
      if (price === null) return;
      try {
        await api(`/api/products/${product.id}`, { method: 'PUT', body: JSON.stringify({ name, price_cop: price }) });
        showToast('Producto actualizado.'); await refreshAll();
      } catch (error) { showToast(error.message, 'error'); }
    });
    const remove = el('button', 'btn btn-danger-text btn-small', 'Desactivar');
    remove.type = 'button';
    remove.addEventListener('click', async () => {
      if (!confirm(`¿Desactivar «${product.name}»? Los pedidos existentes conservarán el precio original.`)) return;
      try {
        await api(`/api/products/${product.id}`, { method: 'DELETE' });
        showToast('Producto desactivado.'); await refreshAll();
      } catch (error) { showToast(error.message, 'error'); }
    });
    actions.append(edit, remove); card.append(meta, actions); root.append(card);
  }
}
function orderCard(order, mode) {
  const card = el('article', 'order-card');
  const top = el('div', 'order-top');
  const title = el('div', 'order-details');
  title.append(el('div', 'order-code', `${order.code}  ·  ${order.customer}`),
               el('div', 'order-date', friendlyDate(mode === 'history' ? (order.prepared_at || order.created_at) : order.created_at)));
  const badge = el('span', `priority-badge ${order.priority === 1 ? 'high' : 'normal'}`,
                   order.priority === 1 ? '↑ Alta' : '• Normal');
  top.append(title, badge);
  const items = el('ul', 'order-items');
  for (const item of order.items) items.append(el('li', '', `${item.quantity} × ${item.name}  ·  ${money(item.subtotal_cop)}`));
  const bottom = el('div', 'order-bottom');
  bottom.append(el('strong', 'order-total-value', money(order.total_cop)));
  if (mode === 'pending') {
    const button = el('button', 'btn btn-danger-text btn-small', 'Cancelar');
    button.type = 'button';
    button.addEventListener('click', async () => {
      if (!confirm(`¿Cancelar ${order.code}?`)) return;
      try {
        await api(`/api/orders/${order.id}/cancel`, { method: 'POST', body: '{}' });
        showToast(`Se canceló ${order.code}.`); await refreshAll();
      } catch (error) { showToast(error.message, 'error'); }
    });
    bottom.append(button);
  }
  card.append(top, items, bottom);
  return card;
}
function pendingList() {
  const root = $('#pendingOrders'); root.replaceChildren();
  if (!state.pending.length) root.append(emptyState('No hay pedidos pendientes', 'Cuando recibas pedidos nuevos aparecerán aquí.'));
  for (const order of state.pending) root.append(orderCard(order, 'pending'));
  $('#pendingCounter').textContent = `${state.stats.orders_pending || 0} en espera`;
  $('#pendingLimitNotice').hidden = (state.stats.orders_pending || 0) <= state.pending.length;
}
function historyList() {
  const root = $('#historyList'); root.replaceChildren();
  if (!state.history.length) root.append(emptyState('Aún no hay pedidos preparados', 'Los pedidos aparecerán cuando se preparen.'));
  for (const order of state.history) root.append(orderCard(order, 'history'));
  $('#historyCounter').textContent = `Mostrando ${state.history.length} de ${state.stats.orders_prepared || 0}`;
  $('#loadMoreHistory').hidden = state.history.length >= (state.stats.orders_prepared || 0);
  $('#clearHistory').disabled = !state.stats.orders_prepared;
}
function renderMetrics() {
  $('#mProducts').textContent = (state.stats.products_active || 0).toLocaleString('es-CO');
  $('#mPending').textContent = (state.stats.orders_pending || 0).toLocaleString('es-CO');
  $('#mPrepared').textContent = (state.stats.orders_prepared || 0).toLocaleString('es-CO');
  $('#mPriority').textContent = (state.stats.priority_queue_size || 0).toLocaleString('es-CO');
  $('#processNext').disabled = !state.stats.orders_pending;
}
async function refreshAll() {
  try {
    const [stats, products, pending, history] = await Promise.all([
      api('/api/status'), api('/api/products'), api('/api/orders/pending?limit=60'),
      api(`/api/history?limit=${state.historyLimit}&offset=0`)
    ]);
    state.stats = stats; state.products = products; state.pending = pending;
    state.history = history; state.historyOffset = history.length;
    renderMetrics(); productPicker(); menuList(); pendingList(); historyList();
    $('#connectionStatus').textContent = 'Servidor conectado';
    $('#connectionDot').className = 'connection-dot online';
  } catch (error) {
    $('#connectionStatus').textContent = 'Sin conexión';
    $('#connectionDot').className = 'connection-dot offline';
    showToast(error.message, 'error');
  }
}

$('#orderForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const inputs = $$('#orderProducts .qty');
  if (inputs.some(input => !Number.isInteger(Number(input.value)) || Number(input.value) < 0 || Number(input.value) > 99)) {
    showToast('Las cantidades deben ser enteros entre 0 y 99.', 'error'); return;
  }
  const items = inputs.map((input) => ({ product_id: input.dataset.productId, quantity: Number(input.value) }))
    .filter(item => item.quantity > 0);
  try {
    const order = await api('/api/orders', {
      method: 'POST', body: JSON.stringify({ customer: $('#customer').value,
        priority: Number($('#priority').value), items })
    });
    event.target.reset();
    showToast(`${order.code} registrado correctamente.`); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});
$('#productForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    await api('/api/products', { method: 'POST', body: JSON.stringify({
      name: $('#productName').value, price_cop: $('#productPrice').value
    }) });
    event.target.reset(); showToast('Producto agregado al menú.'); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});
$('#processNext').addEventListener('click', async () => {
  try {
    const order = await api('/api/orders/process-next', { method: 'POST', body: '{}' });
    showToast(`${order.code} marcado como preparado.`); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});
$('#clearHistory').addEventListener('click', async () => {
  if (!confirm('¿Borrar únicamente el último pedido preparado? Esta acción es irreversible.')) return;
  try {
    const result = await api('/api/history/last', { method: 'DELETE' });
    showToast(`${result.code} eliminado del historial.`); await refreshAll();
  } catch (error) { showToast(error.message, 'error'); }
});
$('#loadMoreHistory').addEventListener('click', async () => {
  try {
    const batch = await api(`/api/history?limit=${state.historyLimit}&offset=${state.historyOffset}`);
    state.history.push(...batch); state.historyOffset += batch.length;
    historyList();
  } catch (error) { showToast(error.message, 'error'); }
});
$$('.nav-link').forEach(button => button.addEventListener('click', () => {
  $$('.nav-link').forEach(element => element.classList.toggle('active', element === button));
  $$('.tab-panel').forEach(element => element.classList.toggle('active', element.id === button.dataset.tab));
}));
function showClock() {
  $('#liveClock').textContent = new Date().toLocaleString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}
showClock(); setInterval(showClock, 30_000);
refreshAll();
