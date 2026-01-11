function renderLinegraphChart(linegraphData) {
  const containerId = "linegraph_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  showLoader(containerId);

  setTimeout(() => {
    // ✅ Collect all unique dates across all series
    let categories = [...new Set(
      linegraphData.series.flatMap(s => s.data.map(point => point[0]))
    )];

    // ✅ Sort categories chronologically
    categories.sort((a, b) => {
      const [da, ma, ya] = a.split(".");
      const [db, mb, yb] = b.split(".");
      return new Date(+ya, +ma - 1, +da) - new Date(+yb, +mb - 1, +db);
    });

    // ✅ Align each series to categories, fill missing with null
    const seriesData = linegraphData.series.map(s => {
      const dataMap = new Map(s.data.map(point => [point[0], point[1]]));
      return {
        name: s.name,
        data: categories.map(date => dataMap.get(date) ?? null)
      };
    });

    const productName = currentInterfaceText?.product_name || gettext("Unknown product");
    const regionName = currentInterfaceText?.region_name || "";
    const districtName = currentInterfaceText?.district_name || "";
    const dateVisual = currentInterfaceText?.date_visual || "";

    let subtitleParts = [productName];
    if (regionName) subtitleParts.push(regionName);
    if (districtName) subtitleParts.push(districtName);
    if (dateVisual) subtitleParts.push(dateVisual);
    const subtitleText = subtitleParts.join(" — ");

    const styles = getComputedStyle(document.body);
    const bgColor = styles.getPropertyValue("--bg-color").trim();
    const textColor = styles.getPropertyValue("--text-color").trim();

    const chartColors = getChartPalette(seriesData.length);

    const chart = Highcharts.chart(containerId, {
      colors: chartColors,
      chart: {
        type: "line",
        backgroundColor: "transparent",
        zoomType: "x",
        events: {
          fullscreenOpen: function () {
            this.update({
              chart: { backgroundColor: bgColor },
              xAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } }, gridLineWidth: 0 },
              yAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } }, gridLineWidth: 0 },
              subtitle: { style: { color: textColor } },
              legend: { itemStyle: { color: textColor } }
            });
          },
          fullscreenClose: function () {
            this.update({
              chart: { backgroundColor: "transparent" },
              xAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } }, gridLineWidth: 0 },
              yAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } }, gridLineWidth: 0 },
              subtitle: { style: { color: textColor } },
              legend: { itemStyle: { color: textColor } }
            });
          }
        }
      },
      title: { text: "" },
      subtitle: { text: subtitleText, style: { color: textColor } },
      credits: { enabled: false },
      exporting: { enabled: false },
      xAxis: {
        categories: categories,
        title: { text: gettext("Sana"), style: { color: textColor } },
        labels: { rotation: -45, style: { color: textColor } },
        gridLineWidth: 0,
        crosshair: {   // ✅ vertical line on hover
          color: "#888",
          width: 1,
          dashStyle: "ShortDash"
        }
      },
      yAxis: {
        title: {
          text: currentInterfaceText?.data_type === "price" ? gettext("Price (so'm)") : gettext("Narx"),
          style: { color: textColor }
        },
        labels: { style: { color: textColor } },
        gridLineWidth: 0,
        crosshair: {   // ✅ horizontal line on hover
          color: "#888",
          width: 1,
          dashStyle: "ShortDash"
        }
      },
      tooltip: {
        shared: true,
        useHTML: true,
        formatter: function () {
          return this.points
            .slice()
            .sort((a, b) => b.y - a.y)
            .map(p => `
              <span style="color:${p.series.color}">\u25CF</span>
              <b>${p.series.name}</b>: ${Highcharts.numberFormat(p.y, 2, '.', ',')}
            `)
            .join("<br/>");
        }
      },
      legend: {
        enabled: false,
        itemStyle: { color: textColor }
      },
      series: seriesData,
      plotOptions: {
        line: {
          marker: { enabled: false },
          dataLabels: { enabled: false }
        }
      }
    });

    const fullscreenBtn = document.getElementById("fullscreenBtnLinegraph");
    if (fullscreenBtn) {
      fullscreenBtn.addEventListener("click", () => {
        if (chart.fullscreen) {
          chart.fullscreen.toggle();
        }
      });
    }

    hideLoader(containerId);
  }, 1000);
}
