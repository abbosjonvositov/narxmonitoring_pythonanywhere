// product_chart.js

/**
 * SparkLine constructor with sensible defaults
 */
// ✅ Helper function for formatting numbers with space as thousands separator
function formatNumber(num) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num).replace(/,/g, " ");
}

Highcharts.SparkLine = function (a, b, c) {
  const hasRenderToArg = typeof a === "string" || a.nodeName;
  let options = arguments[hasRenderToArg ? 1 : 0];

  const defaultOptions = {
    chart: {
      renderTo: (options.chart && options.chart.renderTo) || (hasRenderToArg && a),
      backgroundColor: null,
      borderWidth: 0,
      type: "area",          // ✅ area chart
      margin: [2, 0, 2, 0],
      width: null,
      height: 30,
      style: { overflow: "visible" },
      skipClone: true
    },
    title: { text: "" },
    credits: { enabled: false },
    exporting: { enabled: false },
    xAxis: {
      type: "datetime",
      labels: { enabled: false },
      title: { text: null },
      startOnTick: false,
      endOnTick: false,
      tickPositions: []
    },
    yAxis: {
      endOnTick: false,
      startOnTick: false,
      labels: { enabled: false },
      title: { text: null }
    },
    legend: { enabled: false },
    tooltip: {
      hideDelay: 0,
      outside: true,
      shared: true,
      style: { zIndex: 9999 }
    },
    plotOptions: {
      series: {
        animation: false,
        lineWidth: 1,
        shadow: false,
        states: { hover: { lineWidth: 1 } },
        marker: { radius: 1, states: { hover: { radius: 2 } } },
        fillOpacity: 0.25   // ✅ area fill opacity
      }
    }
  };

  options = Highcharts.merge(defaultOptions, options);

  return hasRenderToArg
    ? new Highcharts.Chart(a, options, c)
    : new Highcharts.Chart(options, b);
};


// Track current sort state
let currentSort = { column: "change_pct", direction: "desc" };

/**
 * Utility: sort products by column and direction
 */
function sortProducts(products, column, direction) {
  return [...products].sort((a, b) => {
    let valA = a[column];
    let valB = b[column];

    if (column === "name") {
      valA = valA.toLowerCase();
      valB = valB.toLowerCase();
      if (valA < valB) return direction === "asc" ? -1 : 1;
      if (valA > valB) return direction === "asc" ? 1 : -1;
      return 0;
    }

    if (valA < valB) return direction === "asc" ? -1 : 1;
    if (valA > valB) return direction === "asc" ? 1 : -1;
    return 0;
  });
}

/**
 * Render product sparklines inside #product_chart
 */
function renderProductCharts(products) {
  const containerId = "product_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = "";
  showLoader(containerId);

  setTimeout(() => {
    // ✅ Sort products based on currentSort state
    products = sortProducts(products, currentSort.column, currentSort.direction);

    // ✅ Build header row
    const headerRow = document.createElement("div");
    headerRow.className = "product-header";
    headerRow.style.display = "flex";
    headerRow.style.fontWeight = "bold";
    headerRow.style.marginBottom = "8px";
    headerRow.style.position = "sticky";
    headerRow.style.top = "0";
    headerRow.style.background = "#fff";
    headerRow.style.zIndex = "10";
    headerRow.style.paddingTop = "10px";

    const headers = [
      { label: "Mahsulot nomi", key: "name" },
      { label: "Joriy narx", key: "actual" },
      { label: "Avvalgi narx", key: "prev" },
      { label: "O‘zgarish %", key: "change_pct" },
      { label: "Trend", key: null }
    ];

    headers.forEach((h, idx) => {
      const cell = document.createElement("div");
      cell.style.flex = idx === 4 ? "2" : "1";
      cell.style.textAlign = "center";
      cell.textContent = h.label;

      if (h.key) {
        cell.style.cursor = "pointer";
        cell.addEventListener("click", () => {
          if (currentSort.column === h.key) {
            currentSort.direction = currentSort.direction === "asc" ? "desc" : "asc";
          } else {
            currentSort.column = h.key;
            currentSort.direction = "asc";
          }
          renderProductCharts(products);
        });
      }

      headerRow.appendChild(cell);
    });
    container.appendChild(headerRow);

    // ✅ Build product rows
    products.forEach(prod => {
      const changePct = prod.change_pct;

      const row = document.createElement("div");
      row.className = "product-row";
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.marginBottom = "6px";
      row.style.width = "100%";
      row.style.cursor = "pointer";

      // Highlight active product
      if (String(currentFilters.product_id) === String(prod.product_id)) {
        row.classList.add("active-row");
      }

      // ✅ Corrected click handler: only pass newFilters
      row.addEventListener("click", () => {
        const newFilters = { product_id: prod.product_id };
        updateAllCharts(newFilters);
      });

      // Product name
      const nameEl = document.createElement("div");
      nameEl.style.flex = "1";
      nameEl.style.textAlign = "center";
      nameEl.textContent = prod.name;
      row.appendChild(nameEl);

      // Current price
      const actualEl = document.createElement("div");
      actualEl.style.flex = "1";
      actualEl.style.textAlign = "center";
      actualEl.textContent = formatNumber(prod.actual);
      row.appendChild(actualEl);

      // Previous price
      const prevEl = document.createElement("div");
      prevEl.style.flex = "1";
      prevEl.style.textAlign = "center";
      prevEl.textContent = formatNumber(prod.prev);
      row.appendChild(prevEl);

      // Change %
      const changeEl = document.createElement("div");
      changeEl.style.flex = "1";
      changeEl.style.textAlign = "center";
      changeEl.textContent = `${changePct}%`;
      changeEl.style.color = changePct >= 0 ? "green" : "red";
      row.appendChild(changeEl);

      // Sparkline container
      const sparkEl = document.createElement("div");
      sparkEl.className = "sparkline";
      sparkEl.style.flex = "2";
      sparkEl.style.height = "30px";
      row.appendChild(sparkEl);

      container.appendChild(row);

      // ✅ Sparkline chart
      const historyData = prod.history.map(h => [Date.parse(h.date), h.price]);
      const prices = prod.history.map(h => h.price);
      const minPrice = Math.min(...prices);
      const maxPrice = Math.max(...prices);
      const padding = (maxPrice - minPrice) * 0.1 || 100;

      Highcharts.SparkLine(sparkEl, {
        chart: { type: "area", height: 30 },
        xAxis: { type: "datetime", labels: { enabled: false } },
        yAxis: {
          min: minPrice - padding,
          max: maxPrice + padding,
          labels: { enabled: false },
          title: { text: null }
        },
        series: [{ data: historyData }],
        tooltip: {
          headerFormat: `<span style="font-size: 10px">${prod.name}</span><br/>`,
          pointFormatter: function () {
            return `<b>${formatNumber(this.y)}</b> UZS<br/>${Highcharts.dateFormat('%e %b, %Y', this.x)}`;
          },
          style: { zIndex: 9999 }
        }
      });
    });

    hideLoader(containerId);
  }, 1000);
}

// Attach fullscreen toggle for product chart
document.addEventListener("DOMContentLoaded", () => {
  const fullscreenBtnProduct = document.getElementById("fullscreenBtnProduct");
  if (fullscreenBtnProduct) {
    fullscreenBtnProduct.addEventListener("click", () => {
      const chart = Highcharts.charts.find(c => c && c.renderTo.id === "product_chart");
      if (chart && chart.fullscreen) {
        chart.fullscreen.toggle();
      } else {
        const container = document.getElementById("product_chart");
        if (!document.fullscreenElement) {
          container.requestFullscreen().catch(err => {
            console.error("Fullscreen error:", err);
          });
        } else {
          document.exitFullscreen();
        }
      }
    });
  }
});





