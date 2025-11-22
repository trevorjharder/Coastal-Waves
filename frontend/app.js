const API_BASE = 'http://localhost:8000';

async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

async function postJSON(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text);
  }
  return res.json();
}

const state = {
  locations: [],
  stock: [],
  sales: [],
  homeSummary: { on_hand: 0, sold: 0, revenue: 0 },
};

function renderLocations(showHome) {
  const grid = document.getElementById('location-grid');
  grid.innerHTML = '';
  const filtered = state.locations.filter((loc) => loc.is_home === showHome);
  const stockMap = new Map(state.stock.map((s) => [s.location_id, s]));
  const salesMap = new Map(state.sales.map((s) => [s.location_id, s]));

  let tabOnHand = 0;
  let tabSold = 0;
  let tabRevenue = 0;

  filtered.forEach((loc) => {
    const stock = stockMap.get(loc.id) || { on_hand: 0 };
    const sales = salesMap.get(loc.id) || { sold: 0, revenue: 0 };

    tabOnHand += stock.on_hand || 0;
    tabSold += sales.sold || 0;
    tabRevenue += sales.revenue || 0;

    const card = document.createElement('div');
    card.className = 'location-card';
    card.innerHTML = `
      <h3>${loc.name}</h3>
      <p><strong>On hand:</strong> ${stock.on_hand || 0}</p>
      <p><strong>Sold:</strong> ${sales.sold || 0}</p>
      <p><strong>Revenue:</strong> $${(sales.revenue || 0).toFixed(2)}</p>
    `;
    grid.appendChild(card);
  });

  document.querySelector('[data-tab-onhand]').textContent = tabOnHand;
  document.querySelector('[data-tab-sold]').textContent = tabSold;
  document.querySelector('[data-tab-revenue]').textContent = tabRevenue.toFixed(2);
}

async function refreshDashboard(showHome = true) {
  const [locations, stock, sales, home] = await Promise.all([
    fetchJSON('/locations'),
    fetchJSON('/reports/stock'),
    fetchJSON('/reports/sales'),
    fetchJSON('/reports/home'),
  ]);
  state.locations = locations;
  state.stock = stock;
  state.sales = sales;
  state.homeSummary = home;
  document.querySelector('[data-home-onhand]').textContent = home.on_hand;
  document.querySelector('[data-home-sold]').textContent = home.sold;
  document.querySelector('[data-home-revenue]').textContent = home.revenue.toFixed(2);
  renderLocations(showHome);
  populatePaintingOptions();
}

function setupTabs() {
  const homeBtn = document.getElementById('tab-home');
  const externalBtn = document.getElementById('tab-external');

  homeBtn.addEventListener('click', () => {
    homeBtn.classList.add('active');
    externalBtn.classList.remove('active');
    renderLocations(true);
  });

  externalBtn.addEventListener('click', () => {
    externalBtn.classList.add('active');
    homeBtn.classList.remove('active');
    renderLocations(false);
  });
}

async function handlePaintingForm(event) {
  event.preventDefault();
  const form = event.target;
  const payload = {
    code: form.code.value,
    name: form.name.value,
  };
  await postJSON('/paintings', payload);
  form.reset();
  refreshDashboard();
}

async function handleVariantForm(event) {
  event.preventDefault();
  const form = event.target;
  const payload = {
    painting_id: Number(form.painting_id.value),
    category: form.category.value,
    size: form.size.value,
    stretch: form.stretch.checked,
    framing: form.framing.checked,
  };
  await postJSON('/variants', payload);
  form.reset();
  refreshDashboard();
}

function populatePaintingOptions() {
  const select = document.querySelector('#variant-form select[name="painting_id"]');
  select.innerHTML = '';
  state.locations; // keep eslint happy if used later
  fetchJSON('/paintings').then((paintings) => {
    paintings.forEach((p) => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = `${p.code} - ${p.name}`;
      select.appendChild(opt);
    });
  });
}

function bootstrapForms() {
  document.getElementById('painting-form').addEventListener('submit', handlePaintingForm);
  document.getElementById('variant-form').addEventListener('submit', handleVariantForm);
}

setupTabs();
bootstrapForms();
refreshDashboard();
