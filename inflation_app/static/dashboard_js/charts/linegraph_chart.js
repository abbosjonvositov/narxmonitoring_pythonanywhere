function renderLinegraphChart(linegraphData) {
  const containerId = "linegraph_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  showLoader(containerId);

  setTimeout(() => {
    const categories = linegraphData.series[0].data.map(point => point[0]);
    const seriesData = linegraphData.series.map(s => ({
      name: s.name,
      data: s.data.map(point => point[1])
    }));

    const productName = currentInterfaceText?.product_name_latin || "Unknown product";
    const regionName = currentInterfaceText?.region_name_latin || "";
    const districtName = currentInterfaceText?.district_name_latin || "";
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
              xAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } } },
              yAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } } },
              subtitle: { style: { color: textColor } },
              legend: { itemStyle: { color: textColor } }
            });
          },
          fullscreenClose: function () {
            this.update({
              chart: { backgroundColor: "transparent" },
              xAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } } },
              yAxis: { labels: { style: { color: textColor } }, title: { style: { color: textColor } } },
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
        title: { text: "Sana", style: { color: textColor } },
        labels: { rotation: -45, style: { color: textColor } }
      },
      yAxis: {
        title: {
          text: currentInterfaceText?.data_type === "price" ? "Price (so'm)" : "Narx",
          style: { color: textColor }
        },
        labels: { style: { color: textColor } }
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
          marker: { enabled: false }, // ✅ marbles omitted
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
