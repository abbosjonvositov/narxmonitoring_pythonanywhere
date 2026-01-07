// Helper: format numbers with space as thousands separator
function formatNumber(num) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num).replace(/,/g, " ");
}

// Helper: format percentage
function formatPercent(num) {
  return `${num.toFixed(2)}%`;
}

// Track current sort state for region chart only
let currentRegionSort = { column: "pct_change", direction: "desc" };

/**
 * Utility: sort regions by column and direction
 */
function sortRegions(regions, column, direction) {
  return [...regions].sort((a, b) => {
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
 * Render region bar charts inside #region_chart
 */
function renderRegionChart(regions) {
  const containerId = "region_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = "";
  showLoader(containerId);

  // ✅ Shared column sizing
  const COL_FLEX = {
    text: "1",
    bar: "0 0 130px"
  };

  setTimeout(() => {
    // compute pct_change for each region
    regions.forEach(r => {
      r.pct_change = r.prev !== 0
        ? ((r.actual - r.prev) / r.prev) * 100
        : 0;
    });

    // compute global min/max for nominal_change
    const allNominalChanges = regions.map(r => r.nominal_change);
    const globalMin = Math.min(...allNominalChanges);
    const globalMax = Math.max(...allNominalChanges);

    const sortedRegions = sortRegions(
      regions,
      currentRegionSort.column,
      currentRegionSort.direction
    );

    // ================= HEADER =================
    const headerRow = document.createElement("div");
    headerRow.className = "region-header";
    headerRow.style.display = "flex";
    headerRow.style.fontWeight = "bold";
    headerRow.style.marginBottom = "8px";
    headerRow.style.position = "sticky";
    headerRow.style.top = "0";
    headerRow.style.background = "#fff";
    headerRow.style.zIndex = "10";
    headerRow.style.paddingTop = "10px";
    headerRow.style.width = "100%";

    const headers = [
      { label: "Viloyat nomi", key: "name" },
      { label: "Joriy narx", key: "actual" },
      { label: "Avvalgi narx", key: "prev" },
      { label: "O'zgarish %", key: "pct_change" },
      { label: "Nominal o'zgarish (so'm)", key: null }
    ];

    headers.forEach((h, idx) => {
      const cell = document.createElement("div");
      cell.style.flex = idx === 4 ? COL_FLEX.bar : COL_FLEX.text;
      cell.style.minWidth = "0";               // ✅ allow shrink
      cell.style.textAlign = "center";
      cell.textContent = h.label;

      if (h.key) {
        cell.style.cursor = "pointer";
        cell.addEventListener("click", () => {
          if (currentRegionSort.column === h.key) {
            currentRegionSort.direction =
              currentRegionSort.direction === "asc" ? "desc" : "asc";
          } else {
            currentRegionSort.column = h.key;
            currentRegionSort.direction = "asc";
          }
          renderRegionChart(regions);
        });
      }

      headerRow.appendChild(cell);
    });

    container.appendChild(headerRow);

    // ================= ROWS =================
    sortedRegions.forEach(region => {
      const nominalChange = region.nominal_change;
      const pctChange = region.pct_change;

      const row = document.createElement("div");
      row.className = "region-row";
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.marginBottom = "6px";
      row.style.width = "100%";
      row.style.cursor = "pointer";

      if (String(currentFilters.region_id) === String(region.region_id)) {
        row.classList.add("active-row");
      }

      row.addEventListener("click", () => {
        currentFilters.region_id = region.region_id;
        updateMapDrilldown(region.region_id);
      });

      // ---- Region name (safe for long text) ----
      const nameEl = document.createElement("div");
      nameEl.style.flex = COL_FLEX.text;
      nameEl.style.minWidth = "0";              // ✅ CRITICAL
      nameEl.style.whiteSpace = "nowrap";
      nameEl.style.overflow = "hidden";
      nameEl.style.textOverflow = "ellipsis";
      nameEl.style.textAlign = "center";
      nameEl.title = region.name;               // full name on hover
      nameEl.textContent = region.name;
      row.appendChild(nameEl);

      const actualEl = document.createElement("div");
      actualEl.style.flex = COL_FLEX.text;
      actualEl.style.textAlign = "center";
      actualEl.textContent = formatNumber(region.actual);
      row.appendChild(actualEl);

      const prevEl = document.createElement("div");
      prevEl.style.flex = COL_FLEX.text;
      prevEl.style.textAlign = "center";
      prevEl.textContent = formatNumber(region.prev);
      row.appendChild(prevEl);

      const pctEl = document.createElement("div");
      pctEl.style.flex = COL_FLEX.text;
      pctEl.style.textAlign = "center";
      pctEl.textContent = formatPercent(pctChange);
      pctEl.style.color = pctChange >= 0 ? "green" : "red";
      row.appendChild(pctEl);

      const barEl = document.createElement("div");
      barEl.className = "barchart";
      barEl.style.flex = COL_FLEX.bar;
      barEl.style.height = "60px";
      barEl.style.overflow = "hidden";
      row.appendChild(barEl);

      container.appendChild(row);

      Highcharts.chart(barEl, {
        chart: { type: "bar", height: 60, backgroundColor: "#fff" },
        title: { text: "" },
        credits: { enabled: false },
        exporting: { enabled: false },
        xAxis: { categories: [region.name], labels: { enabled: false } },
        yAxis: {
          title: { text: null },
          labels: { enabled: false },
          gridLineWidth: 0,
          min: globalMin,
          max: globalMax
        },
        legend: { enabled: false },
        series: [{
          data: [nominalChange],
          color: nominalChange >= 0 ? "green" : "red"
        }],
        tooltip: {
          pointFormat: `<b>{point.y}</b> nominal change`
        },
        plotOptions: {
          series: {
            animation: false,
            borderWidth: 0,
            dataLabels: {
              enabled: true,
              formatter: function () {
                return formatNumber(this.y);
              },
              align: function () {
                return this.y >= 0 ? "right" : "left";
              }
            }
          }
        }
      });
    });

    hideLoader(containerId);
  }, 1000);
}

// Attach fullscreen toggle for region chart
document.addEventListener("DOMContentLoaded", () => {
  const fullscreenBtnRegion = document.getElementById("fullscreenBtnRegion");
  if (fullscreenBtnRegion) {
    fullscreenBtnRegion.addEventListener("click", () => {
      const chart = Highcharts.charts.find(c => c && c.renderTo.id === "region_chart");
      if (chart && chart.fullscreen) {
        chart.fullscreen.toggle();
      } else {
        const container = document.getElementById("region_chart");
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
