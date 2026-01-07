function renderLinegraphChart(linegraphData) {
  const containerId = "linegraph_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  showLoader(containerId);

  setTimeout(() => {
    // ✅ Extract categories (dates) from the first series
    const categories = linegraphData.series[0].data.map(point => point[0]);

    // ✅ Build series with only numeric values
    const seriesData = linegraphData.series.map(s => ({
      name: s.name,
      data: s.data.map(point => point[1])
    }));

    // ✅ Build subtitle text from interfaceText
    const productName = currentInterfaceText?.product_name_latin || "Unknown product";
    const regionName = currentInterfaceText?.region_name_latin || "";
    const districtName = currentInterfaceText?.district_name_latin || "";
    const dateVisual = currentInterfaceText?.date_visual || "";

    // Compose subtitle string dynamically
    let subtitleParts = [productName];
    if (regionName) subtitleParts.push(regionName);
    if (districtName) subtitleParts.push(districtName);
    if (dateVisual) subtitleParts.push(dateVisual);
    const subtitleText = subtitleParts.join(" — ");

    const chart = Highcharts.chart(containerId, {
      chart: {
        type: "line",
        backgroundColor: "transparent",
        zoomType: "x",
        events: {
          fullscreenOpen: function () {
            this.update({
              chart: { backgroundColor: "#fff" },
              xAxis: { labels: { style: { color: "#000" } } },
              yAxis: { labels: { style: { color: "#000" } } }
            });
          },
          fullscreenClose: function () {
            this.update({
              chart: { backgroundColor: "transparent" }
            });
          }
        }
      },
      title: {
        text: ""
      },
      subtitle: {
        text: subtitleText
      },
      credits: { enabled: false },
      exporting: { enabled: false },
      xAxis: {
        categories: categories,
        title: { text: "Sana" },
        labels: { rotation: -45 }
      },
      yAxis: {
        title: {
          text:
            currentInterfaceText?.data_type === "price"
              ? "Price (so'm)"
              : "Narx"
        }
      },
      tooltip: {
        shared: true,
        useHTML: true,
        formatter: function () {
          return this.points
            .slice()
            .sort((a, b) => b.y - a.y)
            .map(p => {
              return `
                <span style="color:${p.series.color}">\u25CF</span>
                <b>${p.series.name}</b>: ${Highcharts.numberFormat(p.y, 2, '.', ',')}
              `;
            })
            .join("<br/>");
        }
      },
      legend: {
        enabled: false
      },
      series: seriesData,
      plotOptions: {
        line: {
          marker: { enabled: true },
          dataLabels: { enabled: false }
        }
      }
    });

    // ✅ Fullscreen toggle button
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
