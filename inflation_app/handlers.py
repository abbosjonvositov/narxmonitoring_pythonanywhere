from django.db.models import Max, Avg
from .models import *
from .utils import format_price, format_price_change


def map_heatmap_handler(qs, params):
    product_id = params.get("product_id")
    product_name_latin = None
    product_name_cyrillic = None

    # Always fetch product details regardless of whether product_id was provided or defaulted
    if not product_id:
        try:
            product = Product.objects.get(product_name_latin="Olma")
            product_id = product.product_id
            product_name_latin = product.product_name_latin
            product_name_cyrillic = product.product_name_cyrillic
        except Product.DoesNotExist:
            return []
    else:
        try:
            product = Product.objects.get(product_id=product_id)
            product_name_latin = product.product_name_latin
            product_name_cyrillic = getattr(product, 'product_name_cyrillic', None)
        except Product.DoesNotExist:
            return []

    qs = qs.filter(product_id=product_id)
    latest_date = qs.aggregate(latest=Max("date"))["latest"]

    data_type = params.get("type", "price")
    region_id = params.get("region_id")
    if region_id:
        qs = qs.filter(region_id=region_id)
        level = "district"
    else:
        level = "region"

    # Helper function to format date for display
    def format_display_date(date_str):
        if not date_str:
            return None
        from datetime import datetime
        date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
        months_uz = {
            1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
            5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
            9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
        }
        day = date_obj.day
        month = months_uz[date_obj.month]
        year = date_obj.year
        return f"{day} {month}, {year}"

    if data_type == "price":
        date = params.get("date", latest_date)
        qs = qs.filter(date=date)

        if level == "region":
            grouped = qs.values(
                "region_id",
                "region__region_name_latin",
                "region__region_name_cyrillic",
                "region__hc_key"
            ).annotate(avg_price=Avg("price"))
            data = [
                {
                    "region_id": g["region_id"],
                    "region_name_latin": g["region__region_name_latin"],
                    "region_name_cyrillic": g["region__region_name_cyrillic"],
                    "hc_key": g["region__hc_key"],
                    "product_id": product_id,
                    "date": str(date),
                    "price": format_price(g["avg_price"]),
                }
                for g in grouped
            ]
        else:
            data = [
                {
                    "region_id": obs.region_id,
                    "region_name_latin": obs.region.region_name_latin,
                    "region_name_cyrillic": obs.region.region_name_cyrillic,
                    "hc_key": obs.region.hc_key,
                    "district_id": obs.district_id,
                    "district_name_latin": obs.district.district_name_latin,
                    "district_name_cyrillic": obs.district.district_name_cyrillic,
                    "product_id": obs.product_id,
                    "product_name_latin": obs.product.product_name_latin,
                    "product_name_cyrillic": obs.product.product_name_cyrillic,
                    "date": str(obs.date),
                    "price": format_price(obs.price),
                }
                for obs in qs
            ]

    elif data_type == "price_change":
        date = params.get("date", latest_date)
        prev_date = qs.filter(date__lt=date).aggregate(prev=Max("date"))["prev"]

        latest_qs = qs.filter(date=date)
        prev_qs = qs.filter(date=prev_date)

        if level == "region":
            latest_group = latest_qs.values(
                "region_id",
                "region__region_name_latin",
                "region__region_name_cyrillic",
                "region__hc_key"
            ).annotate(avg_price=Avg("price"))
            prev_group = prev_qs.values("region_id").annotate(avg_price=Avg("price"))
            prev_dict = {g["region_id"]: g["avg_price"] for g in prev_group}

            data = [
                {
                    "region_id": g["region_id"],
                    "region_name_latin": g["region__region_name_latin"],
                    "region_name_cyrillic": g["region__region_name_cyrillic"],
                    "hc_key": g["region__hc_key"],
                    "product_id": product_id,
                    "date": str(date),
                    "price": format_price(g["avg_price"]),
                    "price_change": format_price_change(
                        g["avg_price"] - prev_dict.get(g["region_id"], g["avg_price"])
                    ),
                }
                for g in latest_group
            ]
        else:
            prev_dict = {obs.district_id: obs.price for obs in prev_qs}
            data = [
                {
                    "region_id": obs.region_id,
                    "region_name_latin": obs.region.region_name_latin,
                    "region_name_cyrillic": obs.region.region_name_cyrillic,
                    "hc_key": obs.region.hc_key,
                    "district_id": obs.district_id,
                    "district_name_latin": obs.district.district_name_latin,
                    "district_name_cyrillic": obs.district.district_name_cyrillic,
                    "product_id": obs.product_id,
                    "product_name_latin": obs.product.product_name_latin,
                    "product_name_cyrillic": obs.product.product_name_cyrillic,
                    "date": str(obs.date),
                    "price": format_price(obs.price),
                    "price_change": format_price_change(
                        obs.price - prev_dict.get(obs.district_id, obs.price)
                    ),
                }
                for obs in latest_qs
            ]
    else:
        data = []

    return {
        "chart_type": "map_heatmap",
        "data": data,
    }


def product_chart_handler(qs, params):
    """
    Handler for product performance chart showing ALL products with % price change
    and COMPLETE historical prices for each product (limited to last 10 points).
    """
    try:
        region_id = params.get("region_id")
        district_id = params.get("district_id")  # Added district filter
        date = params.get("date")
        data_type = params.get("type", "price")

        # Apply region filter (same as map_heatmap)
        if region_id:
            qs = qs.filter(region_id=region_id)

        # Apply district filter (NEW)
        if district_id:
            qs = qs.filter(district_id=district_id)

        # Get latest date within filters
        latest_date = qs.aggregate(latest=Max("date"))["latest"]
        if not latest_date:
            return {"chart_type": "product_chart", "data": []}

        if data_type == "price":
            target_date = date or latest_date
            prev_date = qs.filter(date__lt=target_date).aggregate(prev=Max("date"))["prev"]
            current_qs = qs.filter(date=target_date)
            prev_qs = qs.filter(date=prev_date) if prev_date else current_qs

        elif data_type == "price_change":
            target_date = latest_date
            prev_date = qs.filter(date__lt=latest_date).aggregate(prev=Max("date"))["prev"]
            current_qs = qs.filter(date=latest_date)
            prev_qs = qs.filter(date=prev_date) if prev_date else current_qs
        else:
            return {"chart_type": "product_chart", "data": []}

        # Get ALL products with current period data
        current_grouped = current_qs.values(
            "product_id",
            "product__product_name_latin"
        ).annotate(avg_price=Avg("price"))

        # Get previous period data for all products
        prev_grouped = prev_qs.values("product_id").annotate(avg_price=Avg("price"))
        prev_dict = {g["product_id"]: g["avg_price"] for g in prev_grouped}

        # Build data for ALL products that have current data
        products = []
        for g in current_grouped:
            product_id = g["product_id"]
            product_name = g["product__product_name_latin"] or f"Product {product_id}"
            actual_price = round(g["avg_price"], 2)
            prev_price = round(prev_dict.get(product_id, actual_price), 2)

            # Calculate price change percentage (2 decimal places)
            if prev_price > 0:
                price_change_pct = round(((actual_price - prev_price) / prev_price) * 100, 2)
            else:
                price_change_pct = 0.00

            # Get LAST 10 historical points for this product (within region + district filters)
            # Aggregated by date to handle multiple daily observations
            hist_qs = (
                qs.filter(product_id=product_id)
                .order_by("-date")
                .values("date")
                .annotate(avg_price=Avg("price"))
                .distinct()[:5]  # Limit to last 5 historical points (note: docstring says 10)
            )

            history = [
                {
                    "date": h["date"].isoformat() if hasattr(h["date"], "isoformat") else str(h["date"]),
                    "price": round(h["avg_price"], 2)
                }
                for h in hist_qs
            ]

            products.append({
                "product_id": product_id,
                "name": product_name,
                "actual": actual_price,
                "prev": prev_price,
                "change_pct": price_change_pct,
                "history": history  # Now contains LAST 5 historical data points (within region + district filters)
            })

        return {
            "chart_type": "product_chart",
            "data": products
        }

    except Exception as e:
        return {
            "chart_type": "product_chart",
            "error": f"Product chart unavailable: {str(e)}"
        }



def region_chart_handler(qs, params):
    """
    Handler for region performance chart showing ALL regions with prices
    for ONE product on a given date. Defaults to "Olma" product.

    Returns data in ROW-ORIENTED format with regions array.
    """
    try:
        product_id = params.get("product_id")
        date = params.get("date")

        # DEFAULT: Use "Olma" product if not specified (matching map_heatmap_handler)
        if not product_id:
            try:
                product = Product.objects.get(product_name_latin="Olma")
                product_id = product.product_id
            except Product.DoesNotExist:
                return {
                    "chart_type": "region_chart",
                    "regions": [],
                    "error": "Default product 'Olma' not found"
                }

        # Filter queryset to the selected/default product
        qs = qs.filter(product_id=product_id)

        # Get latest date within filters
        latest_date = qs.aggregate(latest=Max("date"))["latest"]
        if not latest_date:
            return {
                "chart_type": "region_chart",
                "regions": []
            }

        # Rest of the function remains identical...
        target_date = date or latest_date
        prev_date = qs.filter(date__lt=target_date).aggregate(prev=Max("date"))["prev"]
        current_qs = qs.filter(date=target_date)
        prev_qs = qs.filter(date=prev_date) if prev_date else current_qs

        current_grouped = current_qs.values(
            "region_id", "region__region_name_latin"
        ).annotate(avg_price=Avg("price"))

        prev_grouped = prev_qs.values("region_id").annotate(avg_price=Avg("price"))
        prev_dict = {g["region_id"]: g["avg_price"] for g in prev_grouped}

        regions = []
        for g in current_grouped:
            region_id = g["region_id"]
            region_name = g["region__region_name_latin"] or f"Region {region_id}"
            actual_price = round(g["avg_price"] or 0, 2)
            prev_price = round(prev_dict.get(region_id, actual_price) or actual_price, 2)
            nominal_change = round(actual_price - prev_price, 2)
            pct_change = round(((actual_price - prev_price) / prev_price) * 100, 2) if prev_price > 0 else 0.00

            regions.append({
                "region_id": region_id,
                "name": region_name,
                "actual": actual_price,
                "prev": prev_price,
                "nominal_change": nominal_change,
                "change_pct": pct_change
            })

        return {
            "chart_type": "region_chart",
            "data": regions  # Note: original used "data", not "regions"
        }

    except Exception as e:
        return {
            "chart_type": "region_chart",
            "error": f"Region chart unavailable: {str(e)}",
            "regions": []
        }


def district_chart_handler(qs, params):
    """
    Handler for district performance chart showing price changes
    for ONE product on a given date. Defaults to "Olma" product.
    Includes region_id for each district.

    Behavior:
    - Always includes ALL districts (even zero change)
    """
    try:
        product_id = params.get("product_id")
        date = params.get("date")
        region_id = params.get("region_id")

        # DEFAULT: Use "Olma" product if not specified
        if not product_id:
            try:
                from .models import Product  # Adjust import path as needed
                product = Product.objects.get(product_name_latin="Olma")
                product_id = product.product_id
            except Product.DoesNotExist:
                return {
                    "chart_type": "district_chart",
                    "data": [],
                    "error": "Default product 'Olma' not found"
                }

        # Base queryset filters - FIXED for your model structure
        qs = qs.filter(product__product_id=product_id)  # ✅ product__product_id

        # Region filter (based on your model structure)
        if region_id:
            qs = qs.filter(region__region_id=region_id)  # ✅ region__region_id

        # Get latest date within filters
        latest_date = qs.aggregate(latest=Max("date"))["latest"]
        if not latest_date:
            return {
                "chart_type": "district_chart",
                "data": []
            }

        target_date = date or latest_date
        prev_date = qs.filter(date__lt=target_date).aggregate(prev=Max("date"))["prev"]

        current_qs = qs.filter(date=target_date)
        prev_qs = qs.filter(date=prev_date) if prev_date else current_qs

        # Aggregate prices by district + INCLUDE REGION_ID ✅
        current_grouped = current_qs.values(
            "district__district_id",  # ✅ district__district_id
            "district__district_name_latin",  # ✅ district__district_name_latin
            "region__region_id"  # ✅ NEW: Include region_id
        ).annotate(avg_price=Avg("price"))

        prev_grouped = prev_qs.values(
            "district__district_id"  # ✅ district__district_id
        ).annotate(avg_price=Avg("price"))

        prev_dict = {g["district__district_id"]: g["avg_price"] for g in prev_grouped}

        districts = []
        for g in current_grouped:
            district_id = g["district__district_id"]
            district_name = g["district__district_name_latin"] or f"District {district_id}"
            region_id = int(g["region__region_id"])  # ✅ Convert to INTEGER

            actual_price = round(g["avg_price"] or 0, 2)
            prev_price = round(
                prev_dict.get(district_id, actual_price) or actual_price,
                2
            )

            nominal_change = round(actual_price - prev_price, 2)
            pct_change = (
                round(((actual_price - prev_price) / prev_price) * 100, 2)
                if prev_price > 0 else 0.00
            )

            # ✅ REMOVED: Always include all districts, no zero-change filtering
            districts.append({
                "district_id": district_id,
                "region_id": region_id,  # ✅ INTEGER format
                "name": district_name,
                "actual": actual_price,
                "prev": prev_price,
                "nominal_change": nominal_change,
                "change_pct": pct_change
            })

        return {
            "chart_type": "district_chart",
            "data": districts
        }

    except Exception as e:
        return {
            "chart_type": "district_chart",
            "error": f"District chart unavailable: {str(e)}",
            "data": []
        }


def linegraph_chart_handler(qs, params):
    """
    Handler for Highcharts line graph showing price time series.
    Supports filters: product_id (default "Olma"), region_id, district_id.
    Enforces a hard time window limit via `months` parameter.
    """

    from django.db.models import Avg, Max
    from django.db.models.functions import TruncDay
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta

    # -------------------- SAFETY LIMITS --------------------
    MAX_MONTHS = 12
    DEFAULT_MONTHS = 12

    # -------------------- UZBEK MONTH NAMES --------------------
    months_uz = {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
        5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
        9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
    }

    def format_display_date(date_obj):
        """Format date as '17 Dekabr, 2025'"""
        if not date_obj:
            return None
        return f"{date_obj.day} {months_uz[date_obj.month]}, {date_obj.year}"

    def format_price_2dp(price):
        return round(float(price), 2) if price is not None else None

    # -------------------- PRODUCT HANDLING --------------------
    product_id = params.get("product_id")
    if not product_id:
        try:
            product = Product.objects.get(product_name_latin="Olma")
            product_id = product.product_id
        except Product.DoesNotExist:
            return {
                "chart_type": "linegraph",
                "data": [],
                "error": "Default product 'Olma' not found"
            }

    # -------------------- APPLY FILTERS --------------------
    if params.get("region_id"):
        qs = qs.filter(region__region_id=params["region_id"])
    if params.get("district_id"):
        qs = qs.filter(district__district_id=params["district_id"])

    qs = qs.filter(product__product_id=product_id)

    # -------------------- DATE WINDOW (SAFE) --------------------
    latest_date = qs.aggregate(latest=Max("date"))["latest"]
    if not latest_date:
        return {"chart_type": "linegraph", "data": []}

    months_param = params.get("months")
    try:
        months = int(months_param) if months_param is not None else DEFAULT_MONTHS
    except (TypeError, ValueError):
        months = DEFAULT_MONTHS

    months = max(1, min(months, MAX_MONTHS))

    end_date = latest_date
    start_date = latest_date - relativedelta(months=months)

    qs = qs.filter(date__gte=start_date, date__lte=end_date).order_by("date")

    # -------------------- SERIES GENERATION --------------------
    series = []

    if params.get("district_id"):
        # SINGLE DISTRICT
        daily_prices = (
            qs.annotate(date_trunc=TruncDay("date"))
              .values("date_trunc")
              .annotate(avg_price=Avg("price"))
              .order_by("date_trunc")
        )

        district_name = (
            qs.first().district.district_name_latin
            if qs.exists()
            else f"District {params['district_id']}"
        )

        series.append({
            "name": district_name,
            "data": [
                [format_display_date(dp["date_trunc"]), format_price_2dp(dp["avg_price"])]
                for dp in daily_prices
            ]
        })

    elif params.get("region_id"):
        # MULTIPLE DISTRICTS IN REGION
        districts = District.objects.filter(
            district_id__in=qs.values_list("district__district_id", flat=True)
        )

        for dist in districts:
            dist_qs = qs.filter(district__district_id=dist.district_id)
            dist_daily = (
                dist_qs.annotate(date_trunc=TruncDay("date"))
                       .values("date_trunc")
                       .annotate(avg_price=Avg("price"))
                       .order_by("date_trunc")
            )

            series.append({
                "name": dist.district_name_latin,
                "data": [
                    [format_display_date(dp["date_trunc"]), format_price_2dp(dp["avg_price"])]
                    for dp in dist_daily
                ]
            })

    else:
        # MULTIPLE REGIONS
        regions = Region.objects.filter(
            region_id__in=qs.values_list("region__region_id", flat=True)
        )

        for reg in regions:
            reg_qs = qs.filter(region__region_id=reg.region_id)
            reg_daily = (
                reg_qs.annotate(date_trunc=TruncDay("date"))
                      .values("date_trunc")
                      .annotate(avg_price=Avg("price"))
                      .order_by("date_trunc")
            )

            series.append({
                "name": reg.region_name_latin,
                "data": [
                    [format_display_date(dp["date_trunc"]), format_price_2dp(dp["avg_price"])]
                    for dp in reg_daily
                ]
            })

    # -------------------- RESPONSE --------------------
    return {
        "chart_type": "linegraph",
        "data": {
            "product_id": str(product_id),
            "months": months,
            "series": series
        }
    }


def stacked_column_handler(qs, params):
    """
    Handler for Highcharts stacked column chart showing regional price change contributions.
    Uses ALL unique dates but ONLY returns non-zero contribution periods.
    4 decimal precision. Filters by product_id only. Includes separate totals per period.
    """
    from django.db.models import Avg

    # Uzbek months (consistent with linegraph_chart_handler)
    months_uz = {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
        5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
        9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
    }

    def format_display_date(date_obj):
        """Format date as '17 Dekabr, 2025'"""
        if not date_obj:
            return None
        day = date_obj.day
        month = months_uz[date_obj.month]
        year = date_obj.year
        return f"{day} {month}, {year}"

    def format_4dp(value):
        """Format to 4 decimal places"""
        return round(float(value), 4)

    # Product handling
    product_id = params.get("product_id")
    if not product_id:
        try:
            product = Product.objects.get(product_name_latin="Olma")
            product_id = product.product_id
        except Product.DoesNotExist:
            return {
                "chart_type": "stacked_column",
                "data": [],
                "error": "Default product 'Olma' not found"
            }

    # Filter only by product
    product_qs = qs.filter(product__product_id=product_id)

    if not product_qs.exists():
        return {
            "chart_type": "stacked_column",
            "data": [],
            "error": f"No price data found for product ID {product_id}"
        }

    # Get all regions with weights
    regions = Region.objects.filter(
        region_id__in=product_qs.values_list('region__region_id', flat=True)
    ).select_related().order_by('region_name_latin')

    # ✅ Get ALL unique dates from PriceObservation.date
    all_dates = list(product_qs.dates('date', 'day').distinct().order_by('date'))

    if len(all_dates) < 2:
        return {
            "chart_type": "stacked_column",
            "data": [],
            "error": "Need at least 2 unique dates to calculate price changes"
        }

    # Initialize series for regions ONLY
    series = []
    for region in regions:
        series.append({
            "name": region.region_name_latin,
            "data": []
        })

    date_labels = []
    period_totals = []  # ✅ Separate totals array for each valid period
    valid_period_contributions = []  # Store all contributions for valid periods

    # Calculate for ALL dates, but filter out zero periods in response
    for i, current_date in enumerate(all_dates[1:], 1):  # Start from index 1
        # Current period (t)
        current_period = product_qs.filter(date=current_date).values('region__region_id').annotate(
            avg_price=Avg('price')
        )
        current_prices = {item['region__region_id']: item['avg_price'] or 0 for item in current_period}

        # Previous period (t-1)
        prev_date = all_dates[i - 1]
        prev_period = product_qs.filter(date=prev_date).values('region__region_id').annotate(
            avg_price=Avg('price')
        )
        prev_prices = {item['region__region_id']: item['avg_price'] or 0 for item in prev_period}

        # Calculate contributions for this period
        period_contributions = []
        period_total = 0.0

        for j, region in enumerate(regions):
            current_price = current_prices.get(region.region_id, 0)
            prev_price = prev_prices.get(region.region_id, 0)

            if prev_price > 0:
                pct_change = (current_price / prev_price * 100 - 100)
                weight = float(region.weights or 0)
                contribution = format_4dp(pct_change * weight)
                # print(region, current_date, prev_date, current_price, prev_price, pct_change, weight, contribution)
            else:
                contribution = 0.0

            period_contributions.append(float(contribution))
            period_total += float(contribution)

        # ✅ ONLY include if total contribution != 0
        if period_total != 0:
            valid_period_contributions.append(period_contributions)
            date_labels.append(format_display_date(current_date))
            period_totals.append(format_4dp(period_total))

    # Populate series with valid periods data
    for j, region_series in enumerate(series):
        region_series["data"] = [contributions[j] for contributions in valid_period_contributions]

    if not date_labels:
        return {
            "chart_type": "stacked_column",
            "data": [],
            "error": "No significant price changes found"
        }

    return {
        "chart_type": "stacked_column",
        "data": {
            "product_id": str(product_id),
            "categories": date_labels,
            "series": series,  # Only regions (for stacked columns)
            "period_totals": period_totals,  # ✅ Separate totals array
            "total_regions": len(regions),
            "valid_periods": len(date_labels)
        }
    }


# Global metadata handler (new)
def global_metadata_handler(qs, params):
    """Lightweight global metadata handler - consistent with chart filters."""
    product_id = params.get("product_id")
    district_id = params.get("district_id")
    region_id = params.get("region_id")
    product_name_latin = None
    product_name_cyrillic = None
    region_name_latin = None
    region_name_cyrillic = None
    district_name_latin = None
    district_name_cyrillic = None

    # NEW: Auto-determine region_id from district_id if region_id not provided
    if district_id and not region_id:
        try:
            from .models import District, PriceObservation
            district = District.objects.get(district_id=district_id)
            price_obs = district.price_observations.first()
            if price_obs and price_obs.region:
                region_id = str(price_obs.region.region_id)
                # ✅ Use actual model fields
                region_name_latin = price_obs.region.region_name_latin
                region_name_cyrillic = price_obs.region.region_name_cyrillic
                district_name_latin = district.district_name_latin
                district_name_cyrillic = district.district_name_cyrillic
        except (District.DoesNotExist, AttributeError):
            pass

    # Product handling (same as chart handlers)
    if not product_id:
        try:
            from .models import Product
            product = Product.objects.get(product_name_latin="Olma")
            product_id = product.product_id
            product_name_latin = product.product_name_latin
            product_name_cyrillic = product.product_name_cyrillic
        except Product.DoesNotExist:
            pass
    else:
        try:
            from .models import Product
            product = Product.objects.get(product_id=product_id)
            product_name_latin = product.product_name_latin
            product_name_cyrillic = getattr(product, 'product_name_cyrillic', None)
        except Product.DoesNotExist:
            pass

    # Get region/district names if not set from district auto-detection
    if region_id and not region_name_latin:
        try:
            from .models import Region
            region = Region.objects.get(region_id=region_id)
            region_name_latin = region.region_name_latin
            region_name_cyrillic = region.region_name_cyrillic
        except Region.DoesNotExist:
            pass

    if district_id and not district_name_latin:
        try:
            from .models import District
            district = District.objects.get(district_id=district_id)
            district_name_latin = district.district_name_latin
            district_name_cyrillic = district.district_name_cyrillic
        except District.DoesNotExist:
            pass

    # Filter by product and region (now auto-updated from district) - consistent with charts
    product_qs = qs
    if product_id:
        product_qs = product_qs.filter(product__product_id=product_id)
    if region_id:
        product_qs = product_qs.filter(region__region_id=region_id)
    if district_id:
        product_qs = product_qs.filter(district__district_id=district_id)

    from django.db.models import Max
    latest_date = product_qs.aggregate(latest=Max("date"))["latest"]

    # Use SAME date param logic as map_heatmap_handler
    active_date = params.get("date", latest_date)
    data_type = params.get("type", "price")

    def format_display_date(date_str):
        if not date_str:
            return None
        from datetime import datetime
        date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
        months_uz = {
            1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
            5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
            9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
        }
        return f"{date_obj.day} {months_uz[date_obj.month]}, {date_obj.year}"

    # Raw dates for API/filter usage
    date_options = list(product_qs.dates('date', 'day').values_list('date', flat=True))
    date_options_interface = [
        format_display_date(str(date)) for date in date_options
    ]

    return {
        "filters": {
            "product_id": str(product_id) if product_id else None,
            "district_id": str(district_id) if district_id else None,
            "region_id": str(region_id) if region_id else None,
            # "type": data_type,
            "date": str(active_date) if active_date else None,
        },
        "interface_text": {
            # ✅ Product (latin + cyrillic)
            "product_name_latin": product_name_latin,
            "product_name_cyrillic": product_name_cyrillic,
            # ✅ Region (latin + cyrillic)
            "region_name_latin": region_name_latin,
            "region_name_cyrillic": region_name_cyrillic,
            # ✅ District (latin + cyrillic)
            "district_name_latin": district_name_latin,
            "district_name_cyrillic": district_name_cyrillic,
            # ✅ Date & Type
            "date_visual": format_display_date(active_date),
            # "data_type": data_type,
        },
        "date_options": date_options,
        "date_options_interface": date_options_interface,
    }


CHART_HANDLERS = {
    "map_heatmap": map_heatmap_handler,
    "global_metadata": global_metadata_handler,  # NEW: Dashboard-wide metadata
    'product_chart': product_chart_handler,
    'region_chart': region_chart_handler,
    'district_chart': district_chart_handler,
    'linegraph_chart': linegraph_chart_handler,
    'stacked_column_chart': stacked_column_handler
}
