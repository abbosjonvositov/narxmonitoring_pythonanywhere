let products = [];
let activeIndex = 0;

let tickerInterval = null;
let isPaused = false;

function getHeatmapColor(value, min, max) {
  if (value === 0) return "rgba(153,153,153,0.2)"; // neutral gray

  const ratio = (value - min) / (max - min); // normalize between 0–1

  if (value > 0) {
    return `rgba(76, 175, 80, ${0.2 + ratio * 0.6})`; // green gradient
  } else {
    return `rgba(244, 67, 54, ${0.2 + (1 - ratio) * 0.6})`; // red gradient
  }
}

function formatWithSpace(num) {
  if (typeof num !== "number") return num;
  return num
    .toLocaleString("fr-FR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })
    .replace(",", "."); // keep dot as decimal separator
}

// --- Fetch products from API ---
async function fetchProducts() {
  try {
    const response = await fetch("/api/products/performance/");
    const data = await response.json();
    products = data.products.map(p => ({
      id: p.product_id,
      name: p.name,
      price: p.price,
      prevPrice: p.prevPrice,
      change: p.change,
      performance: p.performance,
      regions: p.regions
    }));
    renderTablePicker();
    enableManualScroll();
  } catch (err) {
    console.error(gettext("Error fetching products:"), err);
  }
}

// --- Show extra info for active product ---
function showExtraInfo(product) {
  if (!product) return;

  const infoBox = document.getElementById("pctChangeTable");
  const performance = Array.isArray(product.performance) ? product.performance : [];

  // --- Performance Table ---
  if (performance.length > 0) {
    let tableHTML = `
      <p>${product.name}</p>
      <table class="right-bar-performance-table">
        <tr>${performance.map(p => `<th>${gettext(p.period)}</th>`).join("")}</tr>
        <tr>${performance.map(p => {
          let cls = "right-bar-performance-neutral";
          if (p.change.pct > 0) cls = "right-bar-performance-positive";
          else if (p.change.pct < 0) cls = "right-bar-performance-negative";
          return `<td class="${cls}">${formatWithSpace(p.change.pct)}%</td>`;
        }).join("")}</tr>
      </table>
    `;
    infoBox.innerHTML = tableHTML;
  } else {
    infoBox.innerHTML = `<p>${gettext("No performance data available")}</p>`;
  }

  // --- Insights Section ---
  const insightsBox = document.getElementById("regionInsights");
  const regionBox = document.getElementById("regionSummary");

  if (Array.isArray(product.regions) && product.regions.length > 0) {
    let highestIncrease = product.regions.reduce((a, b) =>
      b.change.pct > a.change.pct ? b : a
    );
    let highestDecrease = product.regions.reduce((a, b) =>
      b.change.pct < a.change.pct ? b : a
    );
    let mostExpensive = product.regions.reduce((a, b) =>
      b.price > a.price ? b : a
    );
    let cheapest = product.regions.reduce((a, b) =>
      b.price < a.price ? b : a
    );

    insightsBox.innerHTML = `
      <p>${product.name}</p>
      <table class="right-bar-insights-table">
        <tr>
          <th>${gettext("Koʻrsatkichlar")}</th>
          <th>${gettext("Hududlar")}</th>
          <th>${gettext("Qiymat")}</th>
        </tr>
        <tr>
          <td>${gettext("Eng yuqori oʻsish (%)")}</td>
          <td>${highestIncrease.name}</td>
          <td class="insight-positive">${formatWithSpace(highestIncrease.change.pct)}%</td>
        </tr>
        <tr>
          <td>${gettext("Eng yuqori pasayish (%)")}</td>
          <td>${highestDecrease.name}</td>
          <td class="insight-negative">${formatWithSpace(highestDecrease.change.pct)}%</td>
        </tr>
        <tr>
          <td>${gettext("Eng qimmat")}</td>
          <td>${mostExpensive.name}</td>
          <td class="insight-expensive">${formatWithSpace(mostExpensive.price)}</td>
        </tr>
        <tr>
          <td>${gettext("Eng arzon")}</td>
          <td>${cheapest.name}</td>
          <td class="insight-cheapest">${formatWithSpace(cheapest.price)}</td>
        </tr>
      </table>
    `;

    // --- Compute min/max for gradient ---
    const allChanges = product.regions.flatMap(r => r.performance.map(p => p.change.pct));
    const minChange = Math.min(...allChanges);
    const maxChange = Math.max(...allChanges);

    function getRegionHeatmapColor(value, min, max) {
      if (value === 0) return "rgba(153,153,153,0.2)";
      if (value > 0) return `rgba(76, 175, 80, ${0.2 + value / max * 0.6})`;
      else return `rgba(244, 67, 54, ${0.2 + value / min * 0.6})`;
    }

    let rowsHTML = product.regions.map(region => `
      <tr>
        <td title="${region.name}">${region.name}</td>
        ${region.performance.map(p => {
          const bgColor = getRegionHeatmapColor(p.change.pct, minChange, maxChange);
          return `<td style="background-color:${bgColor}">${formatWithSpace(p.change.pct)}%</td>`;
        }).join("")}
      </tr>
    `).join("");

    regionBox.innerHTML = `
      <p>${product.name}</p>
      <table class="right-bar-region-table">
        <tr>
          <th>${gettext("Hududlar")}</th>
          <th>${gettext("1W")}</th>
          <th>${gettext("1M")}</th>
          <th>${gettext("3M")}</th>
          <th>${gettext("6M")}</th>
          <th>${gettext("YTD")}</th>
          <th>${gettext("1Y")}</th>
        </tr>
        ${rowsHTML}
      </table>
    `;
  } else {
    insightsBox.innerHTML = `<p>${gettext("No regional insights available")}</p>`;
    regionBox.innerHTML = `<p>${gettext("No region data available")}</p>`;
  }
}

// --- Render table picker ---
function renderTablePicker() {
  const container = document.getElementById("right-sidebar-product");
  if (!products || products.length === 0) {
    container.innerHTML = `<p>${gettext("Loading products...")}</p>`;
    return;
  }

  container.innerHTML = `
    <div class="table-picker">
      <div class="table-picker-list">
        ${products.map((p, i) => {
          const arrow = p.change.nominal >= 0 ? "▲" : "▼";
          const arrowClass = p.change.nominal >= 0 ? "arrow-up" : "arrow-down";
          return `
            <div class="table-picker-row ${i === activeIndex ? "active" : ""}" data-index="${i}">
              <span>${p.name}</span>
              <span>${formatWithSpace(p.price)}</span>
              <span>${formatWithSpace(p.prevPrice)}</span>
              <span>${formatWithSpace(p.change.nominal)}</span>
              <span><span class="${arrowClass}">${arrow}</span> ${formatWithSpace(p.change.pct)}%</span>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;

  document.querySelectorAll(".table-picker-row").forEach(row => {
    row.addEventListener("click", () => {
      const index = parseInt(row.getAttribute("data-index"), 10);
      activeIndex = index;
      stopTicker();
      updateTablePicker();
    });
  });

  updateTablePicker();
}

// --- Update table picker position + highlight ---
function updateTablePicker() {
  const list = document.querySelector(".table-picker-list");
  const itemHeight = 40;
  const offset = -(activeIndex * itemHeight) + (itemHeight * 2);
  list.style.transform = `translateY(${offset}px)`;

  const rows = document.querySelectorAll(".table-picker-row");
  rows.forEach((el, i) => el.classList.toggle("active", i === activeIndex));

  if (products[activeIndex]) {
    showExtraInfo(products[activeIndex]);
  }
}

// --- Scroll ticker ---
function scrollTicker() {
  if (!products || products.length === 0) return;
  activeIndex = (activeIndex + 1) % products.length;
  updateTablePicker();
}

// --- Manual scroll ---
function enableManualScroll() {
  const list = document.querySelector(".table-picker-list");
  if (!list) return;

  list.addEventListener("wheel", (event) => {
    event.preventDefault();
    if (!products || products.length === 0) return;

    if (event.deltaY > 0) activeIndex = (activeIndex + 1) % products.length;
    else activeIndex = (activeIndex - 1 + products.length) % products.length;

    stopTicker();
    updateTablePicker();
  }, { passive: false });
}

// --- Ticker controls ---
function startTicker() {
  if (!tickerInterval) {
    tickerInterval = setInterval(scrollTicker, 5000);
    isPaused = false;
  }
}

function stopTicker() {
  if (tickerInterval) {
    clearInterval(tickerInterval);
    tickerInterval = null;
    isPaused = true;
  }
}

// --- Init ---
fetchProducts();

document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("toggleBtn");
  const icon = document.getElementById("toggleIcon");

  if (toggleBtn && icon) {
    toggleBtn.addEventListener("click", () => {
      if (isPaused) {
        startTicker();
        icon.classList.remove("fa-play");
        icon.classList.add("fa-pause");
        toggleBtn.title = gettext("Pause");
      } else {
        stopTicker();
        icon.classList.remove("fa-pause");
        icon.classList.add("fa-play");
        toggleBtn.title = gettext("Resume");
      }
    });
  }

  startTicker();
});
