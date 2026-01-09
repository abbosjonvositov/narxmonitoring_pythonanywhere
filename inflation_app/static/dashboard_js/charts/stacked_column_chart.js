function renderStackedColumnChart(columnData) {
  const containerId = "stacked_column_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  showLoader(containerId);

  setTimeout(() => {
    const categories = columnData.categories;
    const seriesData = columnData.series;
    const periodTotals = columnData.period_totals || [];

    const productName = currentInterfaceText?.product_name_latin || gettext("Unknown product");
    const dateVisual = currentInterfaceText?.date_visual || "";

    let subtitleParts = [];
    if (productName) subtitleParts.push(productName);
    if (dateVisual) subtitleParts.push(dateVisual);
    const subtitleText = subtitleParts.join(" — ");

    // ✅ Read theme colors from CSS variables
    const styles = getComputedStyle(document.body);
    const bgColor = styles.getPropertyValue("--bg-color").trim();
    const textColor = styles.getPropertyValue("--text-color").trim();

    // ✅ Use centralized palette
    const chartColors = getChartPalette(seriesData.length);

    const chart = Highcharts.chart(containerId, {
      colors: chartColors,
      chart: {
        type: "column",
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
        gridLineWidth: 0
      },
      yAxis: {
        min: 0,
        title: { text: gettext("Foizda (%)"), style: { color: textColor } },
        labels: {
          style: { color: textColor },
          formatter: function () { return this.value + "%"; }
        },
        gridLineWidth: 0,
        stackLabels: {
          enabled: true,
          formatter: function () {
            const idx = this.x;
            if (periodTotals && periodTotals[idx] !== undefined) {
              return Highcharts.numberFormat(periodTotals[idx], 2) + "%";
            }
            return this.total + "%";
          },
          style: { fontWeight: "bold", color: textColor }
        }
      },
      tooltip: {
        shared: true,
        useHTML: true,
        formatter: function () {
          const idx = this.points[0].point.index;
          const totalText =
            periodTotals && periodTotals[idx] !== undefined
              ? `<br/><b>${gettext("Total")}:</b> ${Highcharts.numberFormat(periodTotals[idx], 2)}%`
              : "";

          return (
            this.points
              .slice()
              .sort((a, b) => b.y - a.y)
              .map(p => `
                <span style="color:${p.series.color}">\u25CF</span>
                <b>${p.series.name}</b>: ${Highcharts.numberFormat(p.y, 2, '.', ',')}%
              `)
              .join("<br/>") + totalText
          );
        }
      },
      plotOptions: {
        column: {
          stacking: "normal",
          dataLabels: { enabled: false },
          borderWidth: 0,
          borderColor: "transparent"
        }
      },
      legend: {
        enabled: false,
        itemStyle: { color: textColor }
      },
      series: seriesData
    });

    const fullscreenBtn = document.getElementById("fullscreenBtnStackedColumn");
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
