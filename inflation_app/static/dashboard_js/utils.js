// utils.js
async function fetchDashboardData(filters = {}) {
  // ✅ Only include non-null filterables in query string
  const cleanFilters = Object.fromEntries(
    Object.entries(filters).filter(([_, v]) => v != null)
  );

  const params = new URLSearchParams(cleanFilters);
  const url = `/api/dashboard${params.toString() ? "?" + params : ""}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Failed to fetch dashboard data");
  }

  const result = await response.json();

  // ✅ Sync global filters and interface_text from global_metadata
  if (result.global_metadata?.filters) {
    currentFilters = { ...currentFilters, ...result.global_metadata.filters };
  }

  if (result.global_metadata?.interface_text) {
    currentInterfaceText = { ...result.global_metadata.interface_text };
  }

  console.log("Filters:", currentFilters);
  console.log("Interface text:", currentInterfaceText);

  return result;
}


// Global filters state
let currentInterfaceText = {};
let currentFilters = {};
let isInDrilldown = false; // track drilldown state


async function updateMapDrilldown(regionId) {
  if (!mapChart) return;

  if (!regionId) {
    // ✅ Drill up if region_id is null
    if (isInDrilldown) {
      mapChart.drillUp();
      isInDrilldown = false;
      currentFilters.region_id = null;
    }
    return;
  }

  // ✅ Otherwise drill down into the region
  const hcKey = hcKeyMap[regionId];
  const point = mapChart.series[0].points.find(p => p['hc-key'] === hcKey);

  if (point) {
    try {
      await drilldownHandler.call(mapChart, { seriesOptions: null, point });
      // 🔑 Mark drilldown state in globals
      isInDrilldown = true;
      currentFilters.region_id = regionId;
    } catch (err) {
      console.error("Map drilldown error:", err);
    }
  } else {
    console.warn("No matching point found for region_id:", regionId);
  }
}

async function updateAllCharts(newFilters = {}, options = {}) {
  try {
    currentFilters = { ...currentFilters, ...newFilters };

    const dashboardData = options.dashboardData || await fetchDashboardData(currentFilters);

    if (!options.skipInterfaceText && dashboardData.interface_text) {
      currentInterfaceText = dashboardData.interface_text;
    }

    // ✅ Always refresh footer info after currentInterfaceText is set/retained
    updateFooterInfo();

    if (dashboardData.global_metadata?.date_options_interface) {
      populateDateDropdown(
        dashboardData.global_metadata.date_options,
        dashboardData.global_metadata.date_options_interface,
        currentFilters.date
      );
    }

    if (!options.skipMap && dashboardData.charts?.map_heatmap?.data) {
      if (!isInDrilldown) {
        renderMapHeatmap(dashboardData.charts.map_heatmap.data, currentInterfaceText);
      } else {
        const mapResult = dashboardData.charts.map_heatmap;
        const districtData = mapChart.series[0].data.map(point => {
          const match = mapResult.data.find(d =>
            d.district_name_latin?.trim().toLowerCase() === point.name.trim().toLowerCase()
          );
          return {
            ...point.options,
            value: match ? match.price : null,
            name: match ? match.district_name_latin : point.name
          };
        });

        mapChart.series[0].setData(districtData);
        const productName = currentInterfaceText?.product_name_latin || "Unknown product";
        const formattedDate = currentInterfaceText?.date_visual || "";
        mapChart.setSubtitle({
          text: `${productName} — ${formattedDate} — ${mapChart.series[0].name}`
        });
      }
    }

    if (dashboardData.charts?.product_chart?.data) {
      renderProductCharts(dashboardData.charts.product_chart.data);
    }
    if (dashboardData.charts?.region_chart?.data) {
      renderRegionChart(dashboardData.charts.region_chart.data);
    }
    if (dashboardData.charts?.district_chart?.data) {
      renderDistrictChart(dashboardData.charts.district_chart.data);
    }
    if (dashboardData.charts?.linegraph_chart?.data) {
      renderLinegraphChart(dashboardData.charts.linegraph_chart.data);
    }
    if (dashboardData.charts?.stacked_column_chart?.data) {
      renderStackedColumnChart(dashboardData.charts.stacked_column_chart.data);
    }

    renderAppliedFilters();

  } catch (err) {
    console.error("Failed to update charts:", err);
  }
}

// Central update function
//async function updateAllCharts(newFilters = {}, options = {}) {
//  try {
//    currentFilters = { ...currentFilters, ...newFilters };
//
//    const dashboardData = options.dashboardData || await fetchDashboardData(currentFilters);
//
//    if (!options.skipMap) {
//      if (isInDrilldown && currentFilters.region_id) {
//        const regionId = currentFilters.region_id;
//        const fileName = drilldownFileMap[regionId];
//
//        const topology = await fetch(staticMapsBase + fileName + ".json").then(r => r.json());
//        const mapResult = dashboardData.charts.map_heatmap;
//
//        const districtShapes = Highcharts.geojson(topology);
//        const districtData = districtShapes.map(shape => {
//          const shapeNameRaw =
//            shape.properties.NAME_2 ||
//            shape.properties.VARNAME_2 ||
//            shape.properties.name ||
//            shape.properties.id ||
//            "";
//          const shapeName = shapeNameRaw.trim().toLowerCase();
//
//          const match = mapResult.data.find(d => {
//            if (!d || !d.district_name_latin) return false;
//            let dbName = d.district_name_latin.trim().toLowerCase();
//            dbName = dbName.replace(" tumani", "").replace(" district", "");
//            return dbName === shapeName;
//          });
//
//          return {
//            ...shape,
//            value: match ? match.price : null,
//            name: match ? match.district_name_latin : shapeNameRaw
//          };
//        });
//
//        mapChart.series[0].setData(districtData);
//
//        const productName = currentInterfaceText?.product_name_latin || "Unknown product";
//        const productNameCyrillic = currentInterfaceText?.product_name_cyrillic || "";
//        const formattedDate = currentInterfaceText?.date_visual || "";
//        mapChart.setSubtitle({
//          text: `${productName} — ${formattedDate} — ${mapChart.series[0].name}`
//        });
//
//      } else {
//        const mapData = dashboardData.charts.map_heatmap;
//        renderMapHeatmap(mapData.data, currentInterfaceText);
//      }
//    }
//
//    if (dashboardData.charts?.product_chart?.data) {
//      renderProductCharts(dashboardData.charts.product_chart.data);
//    }
//
//    if (dashboardData.charts?.region_chart?.data) {
//      renderRegionChart(dashboardData.charts.region_chart.data);
//    }
//
//    if (dashboardData.charts?.district_chart?.data) {
//      renderDistrictChart(dashboardData.charts.district_chart.data);
//    }
//
//  } catch (err) {
//    console.error("Failed to update charts:", err);
//  }
//}


function populateDateDropdown(dateOptions, dateOptionsInterface, selectedDate) {
  dateDropdownContainer.innerHTML = "";

  const select = document.createElement("select");
  select.className = "form-control d-inline-block";
  select.style.width = "auto";

  dateOptions.forEach((dateValue, idx) => {
    const option = document.createElement("option");
    option.value = dateValue;
    option.textContent = dateOptionsInterface[idx];
    if (dateValue === selectedDate) {
      option.selected = true;
    }
    select.appendChild(option);
  });

  select.addEventListener("change", e => {
    const chosenDate = e.target.value;
    currentFilters = { ...currentFilters, date: chosenDate };
    updateAllCharts(currentFilters, { skipInterfaceText: true });
    // renderAppliedFilters(); <-- no longer needed here, handled in updateAllCharts
  });

  dateDropdownContainer.appendChild(select);

  // ✅ Initial render of filters
  renderAppliedFilters();
}


function renderAppliedFilters() {
  const container = document.getElementById("appliedFiltersContainer");
  container.innerHTML = "";

  const labelMap = {
    product_id: currentInterfaceText?.product_name_latin,
    region_id: currentInterfaceText?.region_name_latin,
    district_id: currentInterfaceText?.district_name_latin,
    date: currentInterfaceText?.date_visual
  };

  Object.entries(currentFilters).forEach(([key, value]) => {
    if (value) {
      const label = labelMap[key] || value || key; // ✅ fallback to value or key

      const chip = document.createElement("span");
      chip.className = "filter-chip badge badge-dark mr-2";
      chip.innerHTML = `
        <span class="filter-label">${label}</span>
        <button type="button" class="close ml-2" aria-label="Remove">
          <span aria-hidden="true">&times;</span>
        </button>
      `;

      chip.querySelector(".close").addEventListener("click", () => {
        // Remove this filter
        currentFilters[key] = null;

        if (key === "region_id" && mapChart && isInDrilldown) {
          // ✅ Perform drill‑up only, let the drillup event handler refresh charts
          mapChart.drillUp();
          isInDrilldown = false;
          currentFilters.district_id = null; // also clear district
        } else {
          // ✅ For other filters, refresh charts directly
          updateAllCharts(currentFilters, { skipInterfaceText: true });
        }

        // Re-render chips
        renderAppliedFilters();
      });

      container.appendChild(chip);
    }
  });
}


//function updateFooterInfo() {
//  const productName = currentInterfaceText?.product_name_latin || "";
//  const regionName = currentInterfaceText?.region_name_latin || "";
//  const districtName = currentInterfaceText?.district_name_latin || "";
//  const dateVisual = currentInterfaceText?.date_visual || "";
//
//  let footerParts = [];
//  if (productName) footerParts.push(productName);
//  if (regionName) footerParts.push(regionName);
//  if (districtName) footerParts.push(districtName);
//  if (dateVisual) footerParts.push(dateVisual);
//
//  const footerText = footerParts.join(" — ") || "No filter info";
//
//  // ✅ Update district chart footer
//  const districtFooter = document.getElementById("districtFooterInfo");
//  if (districtFooter) {
//    districtFooter.textContent = footerText;
//  }
//}
function updateFooterInfo() {
  const productName = currentInterfaceText?.product_name_latin || "";
  const regionName = currentInterfaceText?.region_name_latin || "";
  const districtName = currentInterfaceText?.district_name_latin || "";
  const dateVisual = currentInterfaceText?.date_visual || "";

  let footerParts = [];
  if (productName) footerParts.push(productName);
  if (regionName) footerParts.push(regionName);
  if (districtName) footerParts.push(districtName);
  if (dateVisual) footerParts.push(dateVisual);

  const footerText = footerParts.join(" — ") || "No filter info";

  // ✅ Update all footer placeholders with the same class
  const footers = document.querySelectorAll(".footerInfo");
  footers.forEach(el => {
    el.textContent = footerText;
  });
}


// Map region_id from backend → hc-key used by Highcharts
const hcKeyMap = {
  1: "uz-qr",  // Qoraqalpog‘iston
  2: "uz-an",  // Andijon
  3: "uz-bu",  // Bukhoro
  4: "uz-ji",  // Jizzakh
  5: "uz-qa",  // Qashqadaryo
  6: "uz-nw",  // Navoiy
  7: "uz-ng",  // Namangan
  8: "uz-sa",  // Samarqand
  9: "uz-su",  // Surkhondaryo
  10: "uz-si", // Sirdaryo
  11: "uz-ta", // Toshkent viloyati
  12: "uz-fa", // Farg‘ona
  13: "uz-kh", // Khorazm
  14: "uz-tk"  // Toshkent shahri
};

const drilldownFileMap = {
  1: "qoraqalpogiston",
  2: "andijon",
  3: "bukhoro",
  4: "jizzakh",
  5: "qashqadaryo",
  6: "navoiy",
  7: "namangan",
  8: "samarqand",
  9: "surkhondaryo",
  10: "sirdaryo",
  11: "toshkent_viloyati",
  12: "fargona",
  13: "xorazm",
  14: "toshkent_shahri"
};

