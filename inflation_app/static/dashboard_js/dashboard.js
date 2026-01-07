document.addEventListener("DOMContentLoaded", async () => {
  const filtersForm = document.getElementById("filtersForm");
  const dateDropdownContainer = document.getElementById("dateDropdownContainer");

  // ✅ Footer updater

  async function loadChart(filters = {}) {
    try {
      const result = await fetchDashboardData(filters);

      // ✅ Extract chart data from backend response
      const mapData = result.charts?.map_heatmap?.data || [];
      const productData = result.charts?.product_chart?.data || [];
      const regionData = result.charts?.region_chart?.data || [];
      const districtData = result.charts?.district_chart?.data || [];
      const linegraphData = result.charts?.linegraph_chart?.data || [];
      const stackedColumnData = result.charts?.stacked_column_chart?.data || []; // NEW

      console.log("Region chart data:", regionData);
      console.log("District chart data:", districtData);
      console.log("Linegraph chart data:", linegraphData);
      console.log("Stacked column chart data:", stackedColumnData); // NEW

      // ✅ Update global interface text
      currentInterfaceText = result.global_metadata?.interface_text || {};

      // ✅ Update footer info
      updateFooterInfo();

      // ✅ Populate date dropdown if metadata is available
      if (dateDropdownContainer && result.global_metadata?.date_options_interface) {
        populateDateDropdown(
          result.global_metadata.date_options,
          result.global_metadata.date_options_interface,
          result.global_metadata.filters?.date
        );
      }

      // ✅ Render map heatmap
      renderMapHeatmap(mapData, currentInterfaceText);

      // ✅ Render product chart if data exists
      if (productData.length > 0) {
        renderProductCharts(productData);
      }

      // ✅ Render region chart
      if (regionData.length > 0) {
        renderRegionChart(regionData);
      }

      // ✅ Render district chart
      if (districtData.length > 0) {
        renderDistrictChart(districtData);
      }

      // ✅ Render linegraph chart
      if (linegraphData.series && linegraphData.series.length > 0) {
        renderLinegraphChart(linegraphData);
      }

      // ✅ Render stacked column chart
      if (stackedColumnData.series && stackedColumnData.series.length > 0) {
        renderStackedColumnChart(stackedColumnData);
      }

    } catch (error) {
      console.error("Error loading chart:", error);
    }
  }

  if (filtersForm) {
    filtersForm.addEventListener("submit", e => {
      e.preventDefault();
      const formData = new FormData(filtersForm);
      const filters = Object.fromEntries(formData.entries());
      loadChart(filters);
    });
  }

  // Initial load → no filters, backend will use defaults
  loadChart();
});
