let mapChart; // global chart reference


async function drilldownFromRegionChart(regionId, regionName, dashboardData) {
  try {
    // ✅ Use already-fetched dashboardData
    const mapResult = dashboardData.charts.map_heatmap;

    // Load the static topology file for the selected region
    const fileName = drilldownFileMap[regionId];
    const topology = await fetch(staticMapsBase + fileName + ".json").then(r => r.json());

    // Convert topology to Highcharts geojson
    const districtShapes = Highcharts.geojson(topology);

    // Match district shapes with backend data
    const districtData = districtShapes.map(shape => {
      const shapeNameRaw =
        shape.properties.NAME_2 ||
        shape.properties.VARNAME_2 ||
        shape.properties.name ||
        shape.properties.id ||
        "";
      const shapeName = shapeNameRaw.trim().toLowerCase();

      const match = mapResult.data.find(d => {
        if (!d || !d.district_name_latin) return false;
        let dbName = d.district_name_latin.trim().toLowerCase();
        dbName = dbName.replace(" tumani", "").replace(" district", "");
        return dbName === shapeName;
      });

      return {
        ...shape,
        value: match ? match.price : null,
        name: match ? match.district_name_latin : shapeNameRaw
      };
    });

    // ✅ Update the map chart with drilldown data
    mapChart.series[0].setData(districtData);

    // ✅ Update subtitle using global interface text
    const productName = currentInterfaceText?.product_name_latin || "Unknown product";
    const productNameCyrillic = currentInterfaceText?.product_name_cyrillic || "";
    const formattedDate = currentInterfaceText?.date_visual || "";

    mapChart.setSubtitle({
      text: `${productName} — ${formattedDate} — ${regionName}`
    });

  } catch (err) {
    console.error("Drilldown error:", err);
  }
}


async function drilldownHandler(e) {
  if (!e.seriesOptions) {
    isInDrilldown = true; // mark drilldown state
    const chart = this;
    const fileName = drilldownFileMap[e.point.region_id];

    chart.showLoading("Loading...");

    try {
      const mergedFilters = { ...currentFilters, region_id: e.point.region_id };

      const [topology, dashboardData] = await Promise.all([
        fetch(staticMapsBase + fileName + ".json").then(r => r.json()),
        fetchDashboardData(mergedFilters)
      ]);

      // ✅ Access chart data via charts.map_heatmap.data
      const mapResult = dashboardData.charts.map_heatmap;

      const districtShapes = Highcharts.geojson(topology);
      const districtData = districtShapes.map(shape => {
        const shapeNameRaw =
          shape.properties.NAME_2 ||
          shape.properties.VARNAME_2 ||
          shape.properties.name ||
          shape.properties.id ||
          "";
        const shapeName = shapeNameRaw.trim().toLowerCase();

        const match = mapResult.data.find(d => {
          if (!d || !d.district_name_latin) return false;
          let dbName = d.district_name_latin.trim().toLowerCase();
          dbName = dbName.replace(" tumani", "").replace(" district", "");
          return dbName === shapeName;
        });

        return {
          ...shape,
          value: match ? match.price : null,
          name: match ? match.district_name_latin : shapeNameRaw
        };
      });

      chart.hideLoading();
      chart.addSeriesAsDrilldown(e.point, {
        name: e.point.name,
        data: districtData,
        dataLabels: { enabled: true, format: "{point.name}" }
      });

      // ✅ Update subtitle using interface_text (Latin only)
      const productName = currentInterfaceText?.product_name_latin || "Unknown product";
      const formattedDate = currentInterfaceText?.date_visual || "";
      chart.setSubtitle({
        text: `${productName} — ${e.point.name} — ${formattedDate}`
      });

      // ✅ Update global filters after drilldown
      currentFilters = mergedFilters;

      // ✅ Pass dashboardData to avoid duplicate request
      updateAllCharts(mergedFilters, { skipMap: true, dashboardData });

    } catch (error) {
      console.error(error);
      chart.hideLoading();
      alert(`Ошибка: ${error.message}`);
    }
  }
}

function renderMapHeatmap(apiData, interfaceText = {}) {
  const containerId = 'map_chart';
  showLoader(containerId);
  console.log("Interface text inside renderMapHeatmap:", interfaceText);

  fetch('https://code.highcharts.com/mapdata/countries/uz/uz-all.topo.json')
    .then(response => response.json())
    .then(topology => {
      // ✅ apiData is already charts.map_heatmap.data
      const data = apiData.map(r => ({
        "hc-key": hcKeyMap[r.region_id],
        value: r.price,
        drilldown: "region-" + r.region_id,
        // Use Latin name for consistency
        name: r.region_name_latin || r.region_name_cyrillic,
        region_id: r.region_id
      }));

      // ✅ Compute dynamic min and max from apiData
      const values = data.map(d => d.value);
      const minValue = Math.min(...values);
      const maxValue = Math.max(...values);

      // ✅ Extract product name + date from interfaceText only
      const productName = interfaceText?.product_name_latin || 'Unknown product';
      const formattedDate = interfaceText?.date_visual || '';

      if (typeof Highcharts !== "undefined") {
        setTimeout(() => {
          if (!mapChart) {
            mapChart = Highcharts.mapChart(containerId, {
              chart: {
                events: {
                  // ✅ Use centralized drilldown handler
                  drilldown: drilldownHandler
                },
                styledMode: false
              },
              title: { text: '' },
              subtitle: {
                text: `${productName} — ${formattedDate}`
              },
              exporting: { buttons: { contextButton: { enabled: false } } },
              // ✅ Dynamic color axis
              colorAxis: {
                min: minValue,
                max: maxValue,
                minColor: '#E6E7E8',
                maxColor: '#005645'
              },
              legend: {
                layout: 'horizontal',
                align: 'center',
                verticalAlign: 'bottom',
                backgroundColor: '#FFFFFF',
                symbolWidth: 300,
                title: { text: 'Narx darajasi', style: { fontSize: '12px' } }
              },
              mapNavigation: { enabled: true, buttonOptions: { verticalAlign: 'bottom' } },
              plotOptions: { map: { states: { hover: { color: '#EEDD66' } } } },
              credits: { enabled: false },
              series: [{
                data,
                mapData: topology,
                joinBy: 'hc-key',
                name: 'Respublika',
                dataLabels: {
                  enabled: true,
                  format: '{point.name}',
                  style: { fontSize: '14px', fontWeight: 'bold', textOutline: '1px black' }
                }
              }],
              drilldown: {
                breadcrumbs: { position: { align: 'right' } },
                activeDataLabelStyle: {
                  color: '#FFFFFF',
                  textDecoration: 'none',
                  textOutline: '1px #000000'
                }
              }
            });

            // ✅ Proper drill‑up handling
            Highcharts.addEvent(mapChart, 'drillup', function () {
              isInDrilldown = false;
              // Reset both region_id and district_id to null
              currentFilters.region_id = null;
              currentFilters.district_id = null;
              // Refresh charts at top level
              setTimeout(() => {
                updateAllCharts(currentFilters);
              }, 0);
            });

            const fullscreenBtn = document.getElementById('fullscreenBtn');
            if (fullscreenBtn) {
              fullscreenBtn.addEventListener('click', () => mapChart.fullscreen.toggle());
            }
          } else {
            // ✅ Refresh existing map
            mapChart.series[0].setData(data);
            mapChart.setSubtitle({
              text: `${productName} — ${formattedDate}`
            });
            // ✅ Update colorAxis dynamically on refresh
            mapChart.colorAxis[0].update({ min: minValue, max: maxValue });
          }

          hideLoader(containerId);
        }, 3000);
      }
    })
    .catch(error => {
      console.error(error);
      hideLoader(containerId);
    });
}
