let mapChart; // global chart reference

async function drilldownFromRegionChart(regionId, regionName, dashboardData) {
  try {
    const mapResult = dashboardData.charts.map_heatmap;

    const fileName = drilldownFileMap[regionId];
    const topology = await fetch(staticMapsBase + fileName + ".json").then(r => r.json());

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

    // ✅ Lock chart while updating
    const container = document.getElementById("map_chart");
    container.style.pointerEvents = "none";
    mapChart.showLoading("Loading...");

    setTimeout(() => {
      mapChart.series[0].setData(districtData);

      const productName = currentInterfaceText?.product_name_latin || "Unknown product";
      const formattedDate = currentInterfaceText?.date_visual || "";

      mapChart.setSubtitle({
        text: `${productName} — ${formattedDate} — ${regionName}`
      });

      // ✅ Unlock chart after update
      mapChart.hideLoading();
      container.style.pointerEvents = "auto";
    }, 2000); // increased delay
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
    chart.renderTo.style.pointerEvents = "none"; // lock interactions

    try {
      const mergedFilters = { ...currentFilters, region_id: e.point.region_id };

      const [topology, dashboardData] = await Promise.all([
        fetch(staticMapsBase + fileName + ".json").then(r => r.json()),
        fetchDashboardData(mergedFilters)
      ]);

      if (dashboardData.global_metadata?.interface_text) {
        const it = dashboardData.global_metadata.interface_text;
        currentInterfaceText = {
          product_name: it.product_name ?? currentInterfaceText?.product_name,
          region_name: it.region_name ?? currentInterfaceText?.region_name,
          district_name: it.district_name ?? currentInterfaceText?.district_name,
          date_visual: it.date_visual ?? currentInterfaceText?.date_visual
        };
      }

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

      setTimeout(() => {
        chart.hideLoading();
        chart.addSeriesAsDrilldown(e.point, {
          name: e.point.name,
          data: districtData,
          dataLabels: { enabled: true, format: "{point.name}" }
        });

        const productName = currentInterfaceText?.product_name || "Unknown product";
        const formattedDate = currentInterfaceText?.date_visual || "";

        chart.setSubtitle({
          text: `${productName} — ${e.point.name} — ${formattedDate}`
        });

        currentFilters = mergedFilters;
        updateAllCharts(mergedFilters, { skipMap: true, dashboardData });

        chart.renderTo.style.pointerEvents = "auto"; // unlock interactions
      }, 2000); // increased delay
    } catch (error) {
      console.error(error);
      chart.hideLoading();
      chart.renderTo.style.pointerEvents = "auto"; // unlock even on error
      alert(`Ошибка: ${error.message}`);
    }
  }
}

function renderMapHeatmap(apiData, interfaceText = {}) {
  const containerId = 'map_chart';
  const container = document.getElementById(containerId);

  // ✅ Lock interactions while loading
  container.style.pointerEvents = "none";
  showLoader(containerId);

  fetch('https://code.highcharts.com/mapdata/countries/uz/uz-all.topo.json')
    .then(response => response.json())
    .then(topology => {
      const data = apiData.map(r => ({
        "hc-key": hcKeyMap[r.region_id],
        value: r.price,
        drilldown: "region-" + r.region_id,
        name: r.region_name || r.region_name,
        region_id: r.region_id
      }));

      const values = data.map(d => d.value).filter(v => v !== null && v !== undefined);
      let minValue = Math.min(...values);
      let maxValue = Math.max(...values);
      if (minValue === maxValue) {
        minValue *= 0.99;
        maxValue *= 1.01;
      }

      const productName = interfaceText?.product_name || gettext("Unknown product");
      const formattedDate = interfaceText?.date_visual || '';

      if (typeof Highcharts !== "undefined") {
        // ✅ Increased delay before rendering (e.g. 2000ms = 2 seconds)
        setTimeout(() => {
          const styles = getComputedStyle(document.body);
          const bgColor = styles.getPropertyValue("--bg-color").trim();
          const textColor = styles.getPropertyValue("--text-color").trim();

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
                labels: { style: { color: textColor } }
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
              mapNavigation: { enabled: true, buttonOptions: { verticalAlign: 'bottom' } },
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
              labels: { style: { color: textColor } }
            });
          }

          // ✅ Unlock interactions after chart is ready
          container.style.pointerEvents = "auto";
          hideLoader(containerId);
        }, 2000); // delay increased to 2 seconds
      }
    })
    .catch(error => {
      console.error(error);
      container.style.pointerEvents = "auto"; // unlock even on error
      hideLoader(containerId);
    });
}
