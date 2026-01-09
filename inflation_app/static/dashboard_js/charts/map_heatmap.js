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
    isInDrilldown = true;
    const chart = this;
    const fileName = drilldownFileMap[e.point.region_id];

    chart.showLoading("Loading...");

    try {
      const mergedFilters = { ...currentFilters, region_id: e.point.region_id };

      const [topology, dashboardData] = await Promise.all([
        fetch(staticMapsBase + fileName + ".json").then(r => r.json()),
        fetchDashboardData(mergedFilters)
      ]);

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

      // -------------------- ✅ PRICE SCALING (DRILLDOWN) --------------------
      const drilldownValues = districtData
        .map(d => d.value)
        .filter(v => v !== null && v !== undefined);

      if (drilldownValues.length) {
        let minDrill = Math.min(...drilldownValues);
        let maxDrill = Math.max(...drilldownValues);

        // Prevent flat scale
        if (minDrill === maxDrill) {
          minDrill *= 0.99;
          maxDrill *= 1.01;
        }

        chart.colorAxis[0].update(
          { min: minDrill, max: maxDrill },
          false // defer redraw
        );
      }

      chart.hideLoading();

      chart.addSeriesAsDrilldown(e.point, {
        name: e.point.name,
        data: districtData,
        dataLabels: { enabled: true, format: "{point.name}" }
      });

      // -------------------- ✅ SUBTITLE UPDATE --------------------
      const productName = currentInterfaceText?.product_name_latin || "Unknown product";
      const formattedDate = currentInterfaceText?.date_visual || "";

      chart.setSubtitle({
        text: `${productName} — ${e.point.name} — ${formattedDate}`
      });

      // -------------------- ✅ UPDATE FILTER STATE --------------------
      currentFilters = mergedFilters;

      // -------------------- ✅ UPDATE OTHER CHARTS --------------------
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

  fetch('https://code.highcharts.com/mapdata/countries/uz/uz-all.topo.json')
    .then(response => response.json())
    .then(topology => {
      const data = apiData.map(r => ({
        "hc-key": hcKeyMap[r.region_id],
        value: r.price,
        drilldown: "region-" + r.region_id,
        name: r.region_name_latin || r.region_name_cyrillic,
        region_id: r.region_id
      }));

      const values = data
        .map(d => d.value)
        .filter(v => v !== null && v !== undefined);

      let minValue = Math.min(...values);
      let maxValue = Math.max(...values);

      if (minValue === maxValue) {
        minValue *= 0.99;
        maxValue *= 1.01;
      }

      const productName = interfaceText?.product_name_latin || gettext("Unknown product");
      const formattedDate = interfaceText?.date_visual || '';

      if (typeof Highcharts !== "undefined") {
        setTimeout(() => {
          const styles = getComputedStyle(document.body);
          const bgColor = styles.getPropertyValue("--bg-color").trim();
          const textColor = styles.getPropertyValue("--text-color").trim();

          // ✅ Theme‑aware heatmap colors
          const modeSwitcher = document.getElementById("modeSwitcher");
          const mode = modeSwitcher ? modeSwitcher.dataset.mode : "light";

          const minColor = mode === "dark" ? "#2c2c2c" : "#E6E7E8";
          const maxColor = mode === "dark" ? "#4caf50" : "#005645";
          const legendBg = mode === "dark" ? "#2c2c2c" : "#FFFFFF";

          if (!mapChart) {
            mapChart = Highcharts.mapChart(containerId, {
              chart: {
                events: { drilldown: drilldownHandler },
                styledMode: false,
                backgroundColor: "transparent"
              },
              title: { text: '' },
              subtitle: {
                text: `${productName} — ${formattedDate}`,
                style: { color: textColor }
              },
              exporting: { buttons: { contextButton: { enabled: false } } },
              colorAxis: {
                min: minValue,
                max: maxValue,
                minColor: minColor,
                maxColor: maxColor,
                labels: {
                  style: { color: textColor }
                }
              },
              legend: {
                layout: 'horizontal',
                align: 'center',
                verticalAlign: 'bottom',
                backgroundColor: legendBg,
                symbolWidth: 300,
                title: {
                  text: gettext("Narx darajasi"),
                  style: { fontSize: '12px', color: textColor }
                },
                itemStyle: { color: textColor }
              },
              mapNavigation: {
                enabled: true,
                buttonOptions: { verticalAlign: 'bottom' }
              },
              plotOptions: {
                map: {
                  borderColor: "#444",
                  borderWidth: 0.5,
                  states: { hover: { color: "#66bb6a" } }
                }
              },
              credits: { enabled: false },
              series: [{
                data,
                mapData: topology,
                joinBy: 'hc-key',
                name: gettext("Respublika"),
                dataLabels: {
                  enabled: true,
                  format: '{point.name}',
                  style: {
                    fontSize: '14px',
                    fontWeight: 'bold',
                    color: textColor,
                    textOutline: 'none'
                  }
                }
              }],
              drilldown: {
                breadcrumbs: { position: { align: 'right' } },
                activeDataLabelStyle: {
                  color: textColor,
                  textDecoration: 'none',
                  textOutline: 'none'
                }
              }
            });

            Highcharts.addEvent(mapChart, 'drillup', function () {
              isInDrilldown = false;
              currentFilters.region_id = null;
              currentFilters.district_id = null;
              setTimeout(() => { updateAllCharts(currentFilters); }, 0);
            });

            const fullscreenBtn = document.getElementById('fullscreenBtn');
            if (fullscreenBtn) {
              fullscreenBtn.addEventListener('click', () =>
                mapChart.fullscreen.toggle()
              );
            }
          } else {
            mapChart.series[0].setData(data);
            mapChart.setSubtitle({
              text: `${productName} — ${formattedDate}`,
              style: { color: textColor }
            });
            mapChart.colorAxis[0].update({
              min: minValue,
              max: maxValue,
              minColor: minColor,
              maxColor: maxColor,
              labels: {
                style: { color: textColor }
              }
            });
          }

          hideLoader(containerId);
        }, 300);
      }
    })
    .catch(error => {
      console.error(error);
      hideLoader(containerId);
    });
}
