function renderStackedColumnChart(columnData) {
  const containerId = "stacked_column_chart";
  const container = document.getElementById(containerId);
  if (!container) return;

  showLoader(containerId);

  setTimeout(() => {
    const categories = columnData.categories;
    const seriesData = columnData.series;
    const periodTotals = columnData.period_totals || [];

    const productName = currentInterfaceText?.product_name || gettext("Unknown product");
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

    // 🔎 Precompute totals for each category
    const computedTotals = categories.map((_, idx) => {
      return periodTotals && periodTotals[idx] !== undefined
        ? periodTotals[idx]
        : seriesData.reduce((sum, s) => sum + (s.data[idx] || 0), 0);
    });

    // Find top 5 highest and lowest indexes
    const sorted = computedTotals
      .map((val, idx) => ({ val, idx }))
      .sort((a, b) => a.val - b.val);

    const lowest5 = sorted.slice(0, 5).map(o => o.idx);
    const highest5 = sorted.slice(-5).map(o => o.idx);
    const showIndexes = new Set([...lowest5, ...highest5]);

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
        title: { text: gettext("Foizda (%)"), style: { color: textColor } },
        labels: {
          style: { color: textColor },
          formatter: function () { return this.value + "%"; }
        },
        gridLineWidth: 0,
        stackLabels: {
          enabled: true,
          allowOverlap: true,
          formatter: function () {
            const idx = this.x;
            const total = periodTotals && periodTotals[idx] !== undefined
              ? periodTotals[idx]
              : this.total;

            // ✅ Only show if index is in top 5 highest or lowest
            if (!showIndexes.has(idx)) return "";
            return total + "%";
          },
          style: { fontWeight: "bold", fontSize: "10px", color: textColor }
        }
      },
      tooltip: {
        shared: true,
        useHTML: true,
        formatter: function () {
          const idx = this.points[0].point.index;
          const totalText =
            periodTotals && periodTotals[idx] !== undefined
              ? `<br/><b>${gettext("Total")}:</b> ${periodTotals[idx]}%`
              : `<br/><b>${gettext("Total")}:</b> ${this.points.reduce((sum, p) => sum + p.y, 0)}%`;

          const header = `<b style="color:#000000;display:block;margin-bottom:4px;">Хисоб фоиз бандда</b>`;

          return (
            header +
            this.points
              .map(p => `
                <span style="color:${p.series.color}">\u25CF</span>
                <b>${p.series.name}</b>: ${p.y}
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
