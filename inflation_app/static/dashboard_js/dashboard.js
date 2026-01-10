document.addEventListener("DOMContentLoaded", async () => {
  const filtersForm = document.getElementById("filtersForm");
  const dateDropdownContainer = document.getElementById("dateDropdownContainer");
  const langForm = document.querySelector("#languageDropdown form");

  async function loadChart(filters = {}) {
    try {
      const result = await fetchDashboardData(filters);

      // ✅ Values are already localized by Django
      const interfaceText = result.global_metadata?.interface_text || {};

      currentInterfaceText = {
        product_name: interfaceText.product_name,
        region_name: interfaceText.region_name,
        district_name: interfaceText.district_name,
        date_visual: interfaceText.date_visual
      };

      updateFooterInfo();

      if (dateDropdownContainer && result.global_metadata?.date_options) {
        // date_options_interface may still be multilingual, so keep lang here
        const lang = window.LANGUAGE_CODE || "en";
        const labels = result.global_metadata.date_options_interface?.[lang] || result.global_metadata.date_options;
        populateDateDropdown(
          result.global_metadata.date_options,
          labels,
          result.global_metadata.filters?.date
        );
      }

      renderMapHeatmap(result.charts?.map_heatmap?.data || [], currentInterfaceText);
      if (result.charts?.product_chart?.data?.length) renderProductCharts(result.charts.product_chart.data);
      if (result.charts?.region_chart?.data?.length) renderRegionChart(result.charts.region_chart.data);
      if (result.charts?.district_chart?.data?.length) renderDistrictChart(result.charts.district_chart.data);
      if (result.charts?.linegraph_chart?.data?.series?.length) renderLinegraphChart(result.charts.linegraph_chart.data);
      if (result.charts?.stacked_column_chart?.data?.series?.length) renderStackedColumnChart(result.charts.stacked_column_chart.data);

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

  if (langForm) {
    langForm.addEventListener("submit", async e => {
      e.preventDefault();
      const formData = new FormData(langForm);

      await fetch(langForm.action, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": formData.get("csrfmiddlewaretoken") }
      });

      // ✅ Update global LANGUAGE_CODE after change
      window.LANGUAGE_CODE = formData.get("language");

      // Reload charts in new language
      loadChart(currentFilters);
    });
  }

  // ✅ Initial load
  loadChart();
});
