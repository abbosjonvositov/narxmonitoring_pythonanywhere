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

// Track current sort state for district chart only
let currentDistrictSort = { column: "pct_change", direction: "desc" };

/**
 * Utility: sort districts by column and direction
 */
function sortDistricts(districts, column, direction) {
  return [...districts].sort((a, b) => {
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
 * Render district bar charts inside #district_chart
 */
function renderDistrictChart(districts) {
  const containerId = "district_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = "";
  showLoader(containerId);

  const COL_FLEX = { text: "1", bar: "0 0 130px" };

  setTimeout(() => {
    districts.forEach(d => { d.pct_change = d.change_pct || 0; });

    const allNominalChanges = districts.map(d => d.nominal_change);
    const globalMin = Math.min(...allNominalChanges);
    const globalMax = Math.max(...allNominalChanges);

    const sortedDistricts = sortDistricts(
      districts,
      currentDistrictSort.column,
      currentDistrictSort.direction
    );

    // ================= HEADER =================
    const headerRow = document.createElement("div");
    headerRow.className = "district-header";
    headerRow.style.display = "flex";
    headerRow.style.fontWeight = "bold";
    headerRow.style.marginBottom = "8px";
    headerRow.style.position = "sticky";
    headerRow.style.top = "0";
    headerRow.style.zIndex = "10";
    headerRow.style.paddingTop = "10px";
    headerRow.style.width = "100%";

    const headers = [
      { label: gettext("Tuman nomi"), key: "name" },
      { label: gettext("Joriy narx"), key: "actual" },
      { label: gettext("Avvalgi narx"), key: "prev" },
      { label: gettext("O'zgarish %"), key: "pct_change" },
      { label: gettext("Nominal o'zgarish (so'm)"), key: null }
    ];

    headers.forEach((h, idx) => {
      const cell = document.createElement("div");
      cell.style.flex = idx === 4 ? COL_FLEX.bar : COL_FLEX.text;
      cell.style.textAlign = "center";
      cell.textContent = h.label;

      if (h.key) {
        cell.style.cursor = "pointer";
        cell.addEventListener("click", () => {
          if (currentDistrictSort.column === h.key) {
            currentDistrictSort.direction =
              currentDistrictSort.direction === "asc" ? "desc" : "asc";
          } else {
            currentDistrictSort.column = h.key;
            currentDistrictSort.direction = "asc";
          }
          renderDistrictChart(districts);
        });
      }

      headerRow.appendChild(cell);
    });

    container.appendChild(headerRow);

    // ================= ROWS =================
    sortedDistricts.forEach(district => {
      const nominalChange = district.nominal_change;
      const pctChange = district.pct_change;

      const row = document.createElement("div");
      row.className = "district-row";
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.marginBottom = "6px";
      row.style.width = "100%";
      row.style.cursor = "pointer";

      if (String(currentFilters.district_id) === String(district.district_id)) {
        row.classList.add("active-row");
      }

      row.addEventListener("click", () => {
        currentFilters = {
          ...currentFilters,
          region_id: district.region_id,
          district_id: district.district_id
        };

        if (!isInDrilldown) {
          updateMapDrilldown(district.region_id);
        } else {
          updateAllCharts(currentFilters);
        }
      });

      const nameEl = document.createElement("div");
      nameEl.style.flex = COL_FLEX.text;
      nameEl.style.textAlign = "center";
      nameEl.style.textOverflow = "ellipsis";
      nameEl.style.overflow = "hidden";
      nameEl.style.whiteSpace = "nowrap";
      nameEl.title = district.district_name;
      nameEl.textContent = district.district_name;
      row.appendChild(nameEl);

      const actualEl = document.createElement("div");
      actualEl.style.flex = COL_FLEX.text;
      actualEl.style.textAlign = "center";
      actualEl.textContent = formatNumber(district.actual);
      row.appendChild(actualEl);

      const prevEl = document.createElement("div");
      prevEl.style.flex = COL_FLEX.text;
      prevEl.style.textAlign = "center";
      prevEl.textContent = formatNumber(district.prev);
      row.appendChild(prevEl);

      const pctEl = document.createElement("div");
      pctEl.style.flex = COL_FLEX.text;
      pctEl.style.textAlign = "center";
      pctEl.textContent = formatPercent(pctChange);
      pctEl.classList.add(pctChange >= 0 ? "positive" : "negative");
      pctEl.title = pctChange >= 0 ? gettext("Ijobiy o'zgarish") : gettext("Salbiy o'zgarish");
      row.appendChild(pctEl);

      const barEl = document.createElement("div");
      barEl.className = "barchart";
      barEl.style.flex = COL_FLEX.bar;
      barEl.style.height = "60px";
      barEl.style.overflow = "hidden";
      row.appendChild(barEl);

      container.appendChild(row);

      Highcharts.chart(barEl, {
        chart: { type: "bar", height: 60, backgroundColor: "transparent" },
        title: { text: "" },
        credits: { enabled: false },
        exporting: { enabled: false },
        xAxis: { categories: [district.name], labels: { enabled: false } },
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
          pointFormat: `<b>{point.y}</b> ${gettext("Nominal o'zgarish")}`
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

// Attach fullscreen toggle for district chart
document.addEventListener("DOMContentLoaded", () => {
  const fullscreenBtnDistrict = document.getElementById("fullscreenBtnDistrict");
  if (fullscreenBtnDistrict) {
    fullscreenBtnDistrict.addEventListener("click", () => {
      const chart = Highcharts.charts.find(c => c && c.renderTo.id === "district_chart");
      if (chart && chart.fullscreen) {
        chart.fullscreen.toggle();
      } else {
        const container = document.getElementById("district_chart");
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