let products = [];
let activeIndex = 0;

let tickerInterval = null;
let isPaused = false;

function getHeatmapColor(value, min, max) {
  if (value === 0) return "rgba(153,153,153,0.2)"; // neutral gray

  const ratio = (value - min) / (max - min); // normalize between 0–1

  if (value > 0) {
    // green gradient: light green → dark green
    return `rgba(76, 175, 80, ${0.2 + ratio * 0.6})`;
  } else {
    // red gradient: light red → dark red
    return `rgba(244, 67, 54, ${0.2 + (1 - ratio) * 0.6})`;
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
    enableManualScroll(); // enable scroll after initial render
  } catch (err) {
    console.error("Error fetching products:", err);
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
        <tr>${performance.map(p => `<th>${p.period}</th>`).join("")}</tr>
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
    infoBox.innerHTML = "<p>No performance data available</p>";
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
        <tr><th>Koʻrsatkichlar</th><th>Hududlar</th><th>Qiymat</th></tr>
        <tr>
          <td>Eng yuqori oʻsish (%)</td>
          <td>${highestIncrease.name}</td>
          <td class="insight-positive">${formatWithSpace(highestIncrease.change.pct)}%</td>
        </tr>
        <tr>
          <td>Eng yuqori pasayish (%)</td>
          <td>${highestDecrease.name}</td>
          <td class="insight-negative">${formatWithSpace(highestDecrease.change.pct)}%</td>
        </tr>
        <tr>
          <td>Eng qimmat</td>
          <td>${mostExpensive.name}</td>
          <td class="insight-expensive">${formatWithSpace(mostExpensive.price)}</td>
        </tr>
        <tr>
          <td>Eng arzon</td>
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
      if (value === 0) return "rgba(153,153,153,0.2)"; // neutral gray

      if (value > 0) {
        const ratio = value / max; // normalize positive values
        return `rgba(76, 175, 80, ${0.2 + ratio * 0.6})`;
      } else {
        const ratio = value / min; // normalize negative values
        return `rgba(244, 67, 54, ${0.2 + ratio * 0.6})`;
      }
    }

    // --- Region Summary with heatmap ---
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
          <th>Hududlar</th>
          <th>1W</th>
          <th>1M</th>
          <th>3M</th>
          <th>6M</th>
          <th>YTD</th>
          <th>1Y</th>
        </tr>
        ${rowsHTML}
      </table>
    `;
  } else {
    insightsBox.innerHTML = "<p>No regional insights available</p>";
    regionBox.innerHTML = "<p>No region data available</p>";
  }
}

// --- Render table picker ---
function renderTablePicker() {
  const container = document.getElementById("right-sidebar-product");
  if (!products || products.length === 0) {
    container.innerHTML = "<p>Loading products...</p>";
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

  // Attach click listeners for manual selection
  document.querySelectorAll(".table-picker-row").forEach(row => {
    row.addEventListener("click", () => {
      const index = parseInt(row.getAttribute("data-index"), 10);
      activeIndex = index;
      stopTicker(); // pause auto-scroll when user clicks
      updateTablePicker();
    });
  });

  updateTablePicker();
}

// --- Update table picker position + highlight ---
function updateTablePicker() {
  const list = document.querySelector(".table-picker-list");
  const itemHeight = 40;
  // shift so activeIndex aligns with middle slot (row 3 of 5)
  const offset = -(activeIndex * itemHeight) + (itemHeight * 2);
  list.style.transform = `translateY(${offset}px)`;

  const rows = document.querySelectorAll(".table-picker-row");
  rows.forEach((el, i) => {
    el.classList.toggle("active", i === activeIndex);
  });

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

// --- Manual scroll with mouse wheel ---
function enableManualScroll() {
  const list = document.querySelector(".table-picker-list");
  if (!list) return;

  list.addEventListener("wheel", (event) => {
    event.preventDefault(); // prevent default page scroll
    if (!products || products.length === 0) return;

    if (event.deltaY > 0) {
      // scroll down → next product
      activeIndex = (activeIndex + 1) % products.length;
    } else {
      // scroll up → previous product
      activeIndex = (activeIndex - 1 + products.length) % products.length;
    }
    stopTicker(); // auto-pause on manual interaction
    updateTablePicker();
  }, { passive: false }); // ensure preventDefault works
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
        // Resume ticker
        startTicker();
        icon.classList.remove("fa-play");
        icon.classList.add("fa-pause");
        toggleBtn.title = "Pause";
      } else {
        // Pause ticker
        stopTicker();
        icon.classList.remove("fa-pause");
        icon.classList.add("fa-play");
        toggleBtn.title = "Resume";
      }
    });
  }

  // Start ticker once DOM is ready
  startTicker();
});


