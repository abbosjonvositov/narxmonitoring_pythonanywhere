// Helper: format numbers with space as thousands separator
function formatNumber(num) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(Math.round(num)).replace(/,/g, " ");
}

// Helper: format percentage without trailing zeros
function formatPercent(num) {
  return `${parseFloat(num.toFixed(2))}%`;
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

  // ✅ Balanced flex ratios: slightly narrower name, wider bar chart
  const COL_FLEX = { name: "1.3", text: "1", bar: "0 0 120px" };

  setTimeout(() => {
    // compute pct_change for each region (frontend calculation)
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
    headerRow.style.zIndex = "10";
    headerRow.style.paddingTop = "10px";
    headerRow.style.width = "100%";

    const headers = [
      { label: gettext("Viloyat nomi"), key: "name" },
      { label: gettext("Joriy narx"), key: "actual" },
      { label: gettext("Avvalgi narx"), key: "prev" },
      { label: gettext("O'zgarish %"), key: "pct_change" },
      { label: gettext("Nominal o'zgarish (so'm)"), key: null }
    ];

    headers.forEach((h, idx) => {
      const cell = document.createElement("div");
      if (idx === 0) {
        cell.style.flex = COL_FLEX.name; // ✅ slightly narrower name column
        cell.style.textAlign = "left";
      } else if (idx === 4) {
        cell.style.flex = COL_FLEX.bar; // ✅ wider bar chart
        cell.style.textAlign = "center";
      } else {
        cell.style.flex = COL_FLEX.text;
        cell.style.textAlign = "center";
      }
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

      const nameEl = document.createElement("div");
      nameEl.style.flex = COL_FLEX.name;
      nameEl.style.textAlign = "left";
      nameEl.style.whiteSpace = "normal";
      nameEl.style.wordBreak = "break-word";
      nameEl.title = region.name;
      nameEl.textContent = region.name;
      row.appendChild(nameEl);

      const actualEl = document.createElement("div");
      actualEl.style.flex = COL_FLEX.text;
      actualEl.style.textAlign = "center";
      actualEl.textContent = formatNumber(Math.round(region.actual)); // ✅ no decimals
      row.appendChild(actualEl);

      const prevEl = document.createElement("div");
      prevEl.style.flex = COL_FLEX.text;
      prevEl.style.textAlign = "center";
      prevEl.textContent = formatNumber(Math.round(region.prev)); // ✅ no decimals
      row.appendChild(prevEl);

      const pctEl = document.createElement("div");
      pctEl.style.flex = COL_FLEX.text;
      pctEl.style.textAlign = "center";
      pctEl.textContent = `${parseFloat(pctChange.toFixed(2))}%`; // ✅ clean percentage
      pctEl.classList.add(pctChange >= 0 ? "positive" : "negative");
      pctEl.title = pctChange >= 0 ? gettext("Ijobiy o'zgarish") : gettext("Salbiy o'zgarish");
      row.appendChild(pctEl);

      const barEl = document.createElement("div");
      barEl.className = "barchart";
      barEl.style.flex = COL_FLEX.bar; // ✅ wider bar chart
      barEl.style.height = "60px";
      barEl.style.overflow = "hidden";
      row.appendChild(barEl);

      container.appendChild(row);

      Highcharts.chart(barEl, {
        chart: { type: "bar", height: 60, backgroundColor: "transparent" },
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
          pointFormatter: function () {
            return `<b>${formatNumber(Math.round(this.y))}</b> ${gettext("Nominal o'zgarish")}`;
          }
        },
        plotOptions: {
          series: {
            animation: false,
            borderWidth: 0,
            dataLabels: {
              enabled: true,
              formatter: function () {
                return formatNumber(Math.round(this.y)); // ✅ no decimals
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
