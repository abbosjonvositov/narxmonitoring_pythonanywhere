function renderStackedColumnChart(columnData) {
  const containerId = "stacked_column_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  showLoader(containerId);

  setTimeout(() => {
    const categories = columnData.categories;
    const seriesData = columnData.series;
    const periodTotals = columnData.period_totals || []; // ✅ totals from endpoint

    const productName = currentInterfaceText?.product_name_latin || "Unknown product";
    const dateVisual = currentInterfaceText?.date_visual || "";

    // ✅ Only product name + date in subtitle
    let subtitleParts = [];
    if (productName) subtitleParts.push(productName);
    if (dateVisual) subtitleParts.push(dateVisual);
    const subtitleText = subtitleParts.join(" — ");

    const chart = Highcharts.chart(containerId, {
      chart: {
        type: "column",
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
      title: { text: "" },
      subtitle: { text: subtitleText },
      credits: { enabled: false },
      exporting: { enabled: false },
      xAxis: {
        categories: categories,
        title: { text: "Sana" },
        labels: { rotation: -45 }
      },
      yAxis: {
        min: 0,
        title: {
          text: "Foizda (%)" // ✅ Axis title updated
        },
        labels: {
          formatter: function () {
            return this.value + "%"; // ✅ Append % to axis labels
          }
        },
        stackLabels: {
          enabled: true,
          formatter: function () {
            // ✅ Use endpoint totals directly (already in %)
            const idx = this.x;
            if (periodTotals && periodTotals[idx] !== undefined) {
              return Highcharts.numberFormat(periodTotals[idx], 2) + "%";
            }
            return this.total + "%"; // fallback if no endpoint value
          },
          style: {
            fontWeight: "bold",
            color: (Highcharts.defaultOptions.title.style &&
              Highcharts.defaultOptions.title.style.color) || "gray"
          }
        }
      },
      tooltip: {
        shared: true,
        useHTML: true,
        formatter: function () {
          const idx = this.points[0].point.index;
          const totalText =
            periodTotals && periodTotals[idx] !== undefined
              ? `<br/><b>Total:</b> ${Highcharts.numberFormat(periodTotals[idx], 2)}%`
              : "";

          return (
            this.points
              .slice()
              .sort((a, b) => b.y - a.y)
              .map(p => {
                return `
                  <span style="color:${p.series.color}">\u25CF</span>
                  <b>${p.series.name}</b>: ${Highcharts.numberFormat(p.y, 2, '.', ',')}%
                `;
              })
              .join("<br/>") + totalText
          );
        }
      },
      plotOptions: {
        column: {
          stacking: "normal",
          dataLabels: { enabled: false }
        }
      },
      legend: { enabled: false }, // ✅ Legend removed
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
