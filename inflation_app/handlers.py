from datetime import timedelta
from django.core.cache import cache
from django.db.models import Avg, Max
from django.db.models.functions import TruncWeek

from .models import Product, Region, District, PriceObservation
from .utils import format_price, format_price_change

CACHE_TIMEOUT = 300  # 5 minutes

MONTHS_UZ = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
    5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
    9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
}

MONTHS_BY_LANG = {
    "uz": {
        1: "Yanvar",
        2: "Fevral",
        3: "Mart",
        4: "Aprel",
        5: "May",
        6: "Iyun",
        7: "Iyul",
        8: "Avgust",
        9: "Sentabr",
        10: "Oktabr",
        11: "Noyabr",
        12: "Dekabr",
    },
    "cy": {
        1: "Январ",
        2: "Феврал",
        3: "Март",
        4: "Апрел",
        5: "Май",
        6: "Июн",
        7: "Июл",
        8: "Август",
        9: "Сентябр",
        10: "Октябр",
        11: "Ноябр",
        12: "Декабр",
    },
    "ru": {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь",
    },
    "en": {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    },
}

# -------------------- Unified Dashboard Handler --------------------


def build_cache_key(params, chart_type="all"):
    """
    Generates a consistent Redis cache key for dashboard charts.
    """
    product_id = params.get("product_id") or "all"
    region_id = params.get("region_id") or "all"
    district_id = params.get("district_id") or "all"
    date = params.get("date") or "latest"
    return f"dashboard:{chart_type}:{product_id}:{region_id}:{district_id}:{date}"


def dashboard_handler(params):
    """
    Unified dashboard handler:
    - Uses Redis caching with get_or_set
    - Shares a filtered queryset for all charts
    - Returns a single JSON payload
    """

    # Shared queryset (with select_related for performance)
    qs = PriceObservation.objects.select_related("product", "region", "district")

    # Apply base filters
    if params.get("product_id"):
        qs = qs.filter(product__product_id=params["product_id"])
    if params.get("region_id"):
        qs = qs.filter(region__region_id=params["region_id"])
    if params.get("district_id"):
        qs = qs.filter(district__district_id=params["district_id"])

    # Inner function to build response (used by cache)
    def build_response():
        response = {
            "map_heatmap": map_heatmap_handler(qs, params),
            "product_chart": product_chart_handler(qs, params),
            "region_chart": region_chart_handler(qs, params),
            "district_chart": district_chart_handler(qs, params),
            "linegraph": linegraph_chart_handler(qs, params),
            "stacked_column": stacked_column_handler(qs, params),
            "metadata": global_metadata_handler(qs, params),
        }
        return response

    # Cache key for the entire dashboard
    cache_key = build_cache_key(params, chart_type="all")
    return cache.get_or_set(cache_key, build_response, CACHE_TIMEOUT)


# -------------------- Individual chart caching --------------------
# Optional: cache individual charts separately if needed

def cached_chart_handler(qs, params, chart_name):
    """
    Fetch a single chart from Redis cache or compute it
    """
    cache_key = build_cache_key(params, chart_type=chart_name)

    chart_handler = CHART_HANDLERS.get(chart_name)
    if not chart_handler:
        return {"chart_type": chart_name, "data": [], "error": "Handler not found"}

    return cache.get_or_set(cache_key, lambda: chart_handler(qs, params), CACHE_TIMEOUT)


# -------------------- Cache invalidation utility --------------------
def invalidate_dashboard_cache(product_id=None, region_id=None, district_id=None, date=None):
    """
    Deletes all relevant cached dashboard keys for a given filter combination
    """
    from itertools import product

    # Allow None to match "all"
    p_vals = [product_id] if product_id else ["all"]
    r_vals = [region_id] if region_id else ["all"]
    d_vals = [district_id] if district_id else ["all"]
    date_vals = [date] if date else ["latest"]

    for chart_type in ["all"] + list(CHART_HANDLERS.keys()):
        for p, r, d, dt in product(p_vals, r_vals, d_vals, date_vals):
            key = f"dashboard:{chart_type}:{p}:{r}:{d}:{dt}"
            cache.delete(key)


# -------------------- Existing Handlers (unchanged logic, optimized qs usage) --------------------

def map_heatmap_handler(qs, params):
    """
    Optimized handler for map heatmap chart.
    - Language-aware REGION names only
    - District names remain unchanged
    """

    from django.db.models import Avg, Max

    # ---------------- LANGUAGE HELPER ----------------
    def get_region_name_field():
        lang = params.get("lang") or params.get("language") or "uz"

        LANG_FIELD_MAP = {
            "uz": "latin",
            "cy": "cyrillic",
            "ru": "russian",
            "en": "english",
        }
        return f"region_name_{LANG_FIELD_MAP.get(lang, 'latin')}"

    # ---------------- PRODUCT RESOLUTION ----------------
    product_id = params.get("product_id")

    if not product_id:
        try:
            product = qs.select_related("product").first().product
            product_id = product.product_id
        except Exception:
            return {"chart_type": "map_heatmap", "data": []}
    else:
        try:
            from .models import Product
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return {"chart_type": "map_heatmap", "data": []}

    qs = qs.filter(product__product_id=product_id)

    latest_date = qs.aggregate(latest=Max("date"))["latest"]

    data_type = params.get("type", "price")
    region_id = params.get("region_id")
    level = "district" if region_id else "region"

    if region_id:
        qs = qs.filter(region__region_id=region_id)

    region_name_field = get_region_name_field()

    # ---------------- PRICE MODE ----------------
    if data_type == "price":
        date = params.get("date", latest_date)
        qs = qs.filter(date=date)

        # -------- REGION LEVEL --------
        if level == "region":
            grouped = qs.values(
                "region_id",
                f"region__{region_name_field}",
                "region__hc_key"
            ).annotate(avg_price=Avg("price"))

            data = [
                {
                    "region_id": g["region_id"],
                    "region_name": g.get(f"region__{region_name_field}")
                        or g.get("region__region_name_latin"),
                    "hc_key": g["region__hc_key"],
                    "product_id": product_id,
                    "date": str(date),
                    "price": format_price(g["avg_price"]),
                }
                for g in grouped
            ]

        # -------- DISTRICT LEVEL (UNCHANGED) --------
        else:
            grouped = qs.values(
                "district_id",
                "district__district_name_latin",
                "district__district_name_cyrillic",
                "region_id",
                "region__region_name_latin",
                "region__region_name_cyrillic",
                "region__hc_key",
                "product_id",
                "product__product_name_latin",
                "product__product_name_cyrillic",
                "date"
            ).annotate(avg_price=Avg("price"))

            data = [
                {
                    "region_id": g["region_id"],
                    "region_name_latin": g["region__region_name_latin"],
                    "region_name_cyrillic": g["region__region_name_cyrillic"],
                    "hc_key": g["region__hc_key"],
                    "district_id": g["district_id"],
                    "district_name_latin": g["district__district_name_latin"],
                    "district_name_cyrillic": g["district__district_name_cyrillic"],
                    "product_id": g["product_id"],
                    "product_name_latin": g["product__product_name_latin"],
                    "product_name_cyrillic": g["product__product_name_cyrillic"],
                    "date": str(g["date"]),
                    "price": format_price(g["avg_price"]),
                }
                for g in grouped
            ]

    # ---------------- PRICE CHANGE MODE ----------------
    elif data_type == "price_change":
        date = params.get("date", latest_date)
        prev_date = qs.filter(date__lt=date).aggregate(prev=Max("date"))["prev"]

        latest_qs = qs.filter(date=date)
        prev_qs = qs.filter(date=prev_date) if prev_date else latest_qs

        # -------- REGION LEVEL --------
        if level == "region":
            latest_group = latest_qs.values(
                "region_id",
                f"region__{region_name_field}",
                "region__hc_key"
            ).annotate(avg_price=Avg("price"))

            prev_group = prev_qs.values("region_id").annotate(avg_price=Avg("price"))
            prev_dict = {g["region_id"]: g["avg_price"] for g in prev_group}

            data = [
                {
                    "region_id": g["region_id"],
                    "region_name": g.get(f"region__{region_name_field}")
                        or g.get("region__region_name_latin"),
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

        # -------- DISTRICT LEVEL (UNCHANGED) --------
        else:
            latest_group = latest_qs.values(
                "district_id",
                "district__district_name_latin",
                "district__district_name_cyrillic",
                "region_id",
                "region__region_name_latin",
                "region__region_name_cyrillic",
                "region__hc_key",
                "product_id",
                "product__product_name_latin",
                "product__product_name_cyrillic",
                "date"
            ).annotate(avg_price=Avg("price"))

            prev_group = prev_qs.values("district_id").annotate(avg_price=Avg("price"))
            prev_dict = {g["district_id"]: g["avg_price"] for g in prev_group}

            data = [
                {
                    "region_id": g["region_id"],
                    "region_name_latin": g["region__region_name_latin"],
                    "region_name_cyrillic": g["region__region_name_cyrillic"],
                    "hc_key": g["region__hc_key"],
                    "district_id": g["district_id"],
                    "district_name_latin": g["district__district_name_latin"],
                    "district_name_cyrillic": g["district__district_name_cyrillic"],
                    "product_id": g["product_id"],
                    "product_name_latin": g["product__product_name_latin"],
                    "product_name_cyrillic": g["product__product_name_cyrillic"],
                    "date": str(g["date"]),
                    "price": format_price(g["avg_price"]),
                    "price_change": format_price_change(
                        g["avg_price"] - prev_dict.get(g["district_id"], g["avg_price"])
                    ),
                }
                for g in latest_group
            ]

    else:
        data = []

    return {
        "chart_type": "map_heatmap",
        "data": data,
    }


def product_chart_handler(qs, params):
    """
    Optimized handler for product performance chart.
    - Shows ALL products with % price change.
    - Returns product names in requested language: uz, cy, ru, en.
    - Includes last N historical points (default: 5).
    """

    try:
        lang = params.get("lang", "uz")
        region_id = params.get("region_id")
        district_id = params.get("district_id")
        date = params.get("date")
        data_type = params.get("type", "price")

        LANG_FIELD_MAP = {
            "uz": "latin",
            "cy": "cyrillic",
            "ru": "russian",
            "en": "english",
        }

        name_field = f"product_name_{LANG_FIELD_MAP.get(lang, 'latin')}"

        # Apply filters
        if region_id:
            qs = qs.filter(region__region_id=region_id)
        if district_id:
            qs = qs.filter(district__district_id=district_id)

        # Get latest date
        latest_date = qs.aggregate(latest=Max("date"))["latest"]
        if not latest_date:
            return {"chart_type": "product_chart", "data": []}

        # Determine target and previous dates
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

        from datetime import datetime

        def format_display_date(date_value):
            if not date_value:
                return None
            if hasattr(date_value, "strftime"):
                date_obj = date_value
            else:
                date_obj = datetime.strptime(str(date_value), "%Y-%m-%d")
            return f"{date_obj.day} {MONTHS_BY_LANG[lang][date_obj.month]}, {date_obj.year}"

        # Aggregate current period data
        current_grouped = current_qs.select_related("product").values(
            "product_id",
            "product__product_name_latin",
            "product__product_name_cyrillic",
            "product__product_name_russian",
            "product__product_name_english"
        ).annotate(avg_price=Avg("price"))

        # Aggregate previous period data
        prev_grouped = prev_qs.values("product_id").annotate(avg_price=Avg("price"))
        prev_dict = {g["product_id"]: g["avg_price"] for g in prev_grouped}

        products = []

        for g in current_grouped:
            product_id = g["product_id"]
            # Select name in requested language
            product_name = g.get(f"product__product_name_{LANG_FIELD_MAP.get(lang, 'latin')}")
            if not product_name:
                # fallback to latin
                product_name = g.get("product__product_name_latin") or f"Product {product_id}"

            actual_price = round(g["avg_price"] or 0, 2)
            prev_price = round(prev_dict.get(product_id, actual_price) or actual_price, 2)

            price_change_pct = (
                round(((actual_price - prev_price) / prev_price) * 100, 2)
                if prev_price > 0 else 0.00
            )

            # Historical series (last 5 points)
            hist_qs = (
                qs.filter(product_id=product_id)
                .select_related("product")
                .values(
                    "date",
                    "product__product_name_latin",
                    "product__product_name_cyrillic",
                    "product__product_name_russian",
                    "product__product_name_english"
                )
                .annotate(avg_price=Avg("price"))
                .order_by("-date")[:5]
            )

            history = []
            for h in hist_qs:
                hist_name = h.get(f"product__product_name_{LANG_FIELD_MAP.get(lang, 'latin')}") or h.get("product__product_name_latin")
                history.append({
                    "date": str(h["date"]),
                    "date_visual": format_display_date(h["date"]),
                    "price": round(h["avg_price"] or 0, 2),
                    "name": hist_name
                })

            products.append({
                "product_id": product_id,
                "name": product_name,
                "actual": actual_price,
                "prev": prev_price,
                "change_pct": price_change_pct,
                "history": list(reversed(history)),  # chronological
            })

        return {
            "chart_type": "product_chart",
            "data": products,
        }

    except Exception as e:
        return {
            "chart_type": "product_chart",
            "error": f"Product chart unavailable: {str(e)}",
        }


def region_chart_handler(qs, params):
    """
    Optimized handler for region performance chart.
    - Shows ALL regions with prices for ONE product on a given date.
    - Defaults to product "Olma" if not specified.
    - Uses shared queryset (already filtered in dashboard_handler).
    - Returns region names in requested language: uz, cy, ru, en.
    """

    try:
        lang = params.get("lang", "uz")
        product_id = params.get("product_id")
        date = params.get("date")

        LANG_FIELD_MAP = {
            "uz": "latin",
            "cy": "cyrillic",
            "ru": "russian",
            "en": "english",
        }
        name_field = f"region_name_{LANG_FIELD_MAP.get(lang, 'latin')}"

        # -------------------- Default product --------------------
        if not product_id:
            try:
                product = Product.objects.get(product_name_latin="Olma")
                product_id = product.product_id
            except Product.DoesNotExist:
                return {
                    "chart_type": "region_chart",
                    "data": [],
                    "error": "Default product 'Olma' not found"
                }

        # Filter queryset to selected product
        qs = qs.filter(product__product_id=product_id)

        # Latest date within filters
        latest_date = qs.aggregate(latest=Max("date"))["latest"]
        if not latest_date:
            return {"chart_type": "region_chart", "data": []}

        target_date = date or latest_date
        prev_date = qs.filter(date__lt=target_date).aggregate(prev=Max("date"))["prev"]

        current_qs = qs.filter(date=target_date)
        prev_qs = qs.filter(date=prev_date) if prev_date else current_qs

        # Aggregate current period data
        current_grouped = current_qs.select_related("region").values(
            "region_id",
            "region__region_name_latin",
            "region__region_name_cyrillic",
            "region__region_name_russian",
            "region__region_name_english",
        ).annotate(avg_price=Avg("price"))

        # Aggregate previous period data
        prev_grouped = prev_qs.values("region_id").annotate(avg_price=Avg("price"))
        prev_dict = {g["region_id"]: g["avg_price"] for g in prev_grouped}

        # -------------------- Date formatting --------------------
        from datetime import datetime

        def format_display_date(date_value):
            if not date_value:
                return None
            if hasattr(date_value, "strftime"):
                date_obj = date_value
            else:
                date_obj = datetime.strptime(str(date_value), "%Y-%m-%d")
            return f"{date_obj.day} {MONTHS_BY_LANG[lang][date_obj.month]}, {date_obj.year}"

        # -------------------- Build response --------------------
        regions = []
        for g in current_grouped:
            region_id = g["region_id"]
            region_name = g.get(f"region__region_name_{LANG_FIELD_MAP.get(lang, 'latin')}") \
                          or g.get("region__region_name_latin") \
                          or f"Region {region_id}"

            actual_price = round(g["avg_price"] or 0, 2)
            prev_price = round(prev_dict.get(region_id, actual_price) or actual_price, 2)
            nominal_change = round(actual_price - prev_price, 2)
            pct_change = (
                round(((actual_price - prev_price) / prev_price) * 100, 2)
                if prev_price > 0 else 0.00
            )

            regions.append({
                "region_id": region_id,
                "name": region_name,
                "actual": actual_price,
                "prev": prev_price,
                "nominal_change": nominal_change,
                "change_pct": pct_change,
                "date": str(target_date),
                "date_visual": format_display_date(target_date)
            })

        return {
            "chart_type": "region_chart",
            "data": regions
        }

    except Exception as e:
        return {
            "chart_type": "region_chart",
            "error": f"Region chart unavailable: {str(e)}",
            "data": []
        }


def district_chart_handler(qs, params):
    """
    Optimized handler for district performance chart.
    - Shows ALL districts with price changes for ONE product on a given date.
    - Defaults to product "Olma" if not specified.
    - Includes region_id for each district.
    - Uses shared queryset (already filtered in dashboard_handler).
    - Returns district and region names in requested language: uz, cy, ru, en.
    """

    try:
        lang = params.get("lang", "uz")
        product_id = params.get("product_id")
        date = params.get("date")
        region_id = params.get("region_id")

        LANG_FIELD_MAP = {
            "uz": "latin",
            "cy": "cyrillic",
            "ru": "russian",
            "en": "english",
        }

        district_name_field = f"district__district_name_{LANG_FIELD_MAP.get(lang, 'latin')}"
        region_name_field = f"region__region_name_{LANG_FIELD_MAP.get(lang, 'latin')}"

        # -------------------- Default product --------------------
        if not product_id:
            try:
                product = Product.objects.get(product_name_latin="Olma")
                product_id = product.product_id
            except Product.DoesNotExist:
                return {
                    "chart_type": "district_chart",
                    "data": [],
                    "error": "Default product 'Olma' not found"
                }

        # Filter queryset to selected product
        qs = qs.filter(product__product_id=product_id)

        # Filter by region if provided
        if region_id:
            qs = qs.filter(region__region_id=region_id)

        # Latest date within filters
        latest_date = qs.aggregate(latest=Max("date"))["latest"]
        if not latest_date:
            return {"chart_type": "district_chart", "data": []}

        target_date = date or latest_date
        prev_date = qs.filter(date__lt=target_date).aggregate(prev=Max("date"))["prev"]

        current_qs = qs.filter(date=target_date)
        prev_qs = qs.filter(date=prev_date) if prev_date else current_qs

        # Aggregate current period data
        current_grouped = current_qs.select_related("district", "region").values(
            "district_id",
            "region_id",
            "district__district_name_latin",
            "district__district_name_cyrillic",
            "district__district_name_russian",
            "district__district_name_english",
            "region__region_name_latin",
            "region__region_name_cyrillic",
            "region__region_name_russian",
            "region__region_name_english"
        ).annotate(avg_price=Avg("price"))

        # Aggregate previous period data
        prev_grouped = prev_qs.values("district_id").annotate(avg_price=Avg("price"))
        prev_dict = {g["district_id"]: g["avg_price"] for g in prev_grouped}

        # -------------------- Date formatting --------------------
        from datetime import datetime

        def format_display_date(date_value):
            if not date_value:
                return None
            if hasattr(date_value, "strftime"):
                date_obj = date_value
            else:
                date_obj = datetime.strptime(str(date_value), "%Y-%m-%d")
            return f"{date_obj.day} {MONTHS_BY_LANG[lang][date_obj.month]}, {date_obj.year}"

        # -------------------- Build response --------------------
        districts = []
        for g in current_grouped:
            district_id = g["district_id"]
            region_id = g["region_id"]

            district_name = g.get(district_name_field) or g.get("district__district_name_latin") or f"District {district_id}"
            region_name = g.get(region_name_field) or g.get("region__region_name_latin") or f"Region {region_id}"

            actual_price = round(g["avg_price"] or 0, 2)
            prev_price = round(prev_dict.get(district_id, actual_price) or actual_price, 2)
            nominal_change = round(actual_price - prev_price, 2)
            pct_change = (
                round(((actual_price - prev_price) / prev_price) * 100, 2)
                if prev_price > 0 else 0.00
            )

            districts.append({
                "district_id": district_id,
                "region_id": region_id,
                "district_name": district_name,
                "region_name": region_name,
                "actual": actual_price,
                "prev": prev_price,
                "nominal_change": nominal_change,
                "change_pct": pct_change,
                "date": str(target_date),
                "date_visual": format_display_date(target_date)
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
    Optimized handler for Highcharts line graph showing WEEKLY price time series.
    - Always returns a full 52-week cycle ending at the latest available week.
    - Uses actual distinct DB dates (no artificial week boundary computation).
    """

    WEEKS_IN_YEAR = 52
    DEFAULT_PRODUCT_NAME = "Olma"

    # ✅ FIXED Uzbek month names (NO DUPLICATES)

    def format_uzbek_date(date_obj):
        if not date_obj:
            return None
        return f"{date_obj.day} {MONTHS_UZ[date_obj.month]}, {date_obj.year}"

    def format_date_ddmmyyyy(date_obj):
        if not date_obj:
            return None
        return date_obj.strftime("%d.%m.%Y")

    def format_price(price):
        return round(float(price), 2) if price is not None else None

    # -------------------- PRODUCT --------------------
    product_id = params.get("product_id")
    if not product_id:
        try:
            product = Product.objects.get(product_name_latin=DEFAULT_PRODUCT_NAME)
            product_id = product.product_id
        except Product.DoesNotExist:
            return {
                "chart_type": "linegraph",
                "data": [],
                "error": f"Default product '{DEFAULT_PRODUCT_NAME}' not found"
            }

    # -------------------- FILTERS --------------------
    qs = qs.filter(product__product_id=product_id)

    if params.get("region_id"):
        qs = qs.filter(region__region_id=params["region_id"])

    if params.get("district_id"):
        qs = qs.filter(district__district_id=params["district_id"])

    # -------------------- DATE WINDOW --------------------
    latest_date = qs.aggregate(latest=Max("date"))["latest"]
    if not latest_date:
        return {"chart_type": "linegraph", "data": []}

    # Use actual DB dates, not computed week boundaries
    end_date = latest_date

    # Get distinct ordered dates
    dates = (
        qs.values_list("date", flat=True)
        .distinct()
        .order_by("date")
    )

    if dates.count() >= WEEKS_IN_YEAR:
        start_date = dates[dates.count() - WEEKS_IN_YEAR]
    else:
        start_date = dates.first()

    qs = qs.filter(date__gte=start_date, date__lte=end_date)

    # -------------------- SERIES --------------------
    series = []

    def generate_weekly_series(filtered_qs, name):
        weekly_prices = (
            filtered_qs
            .values("date")
            .annotate(avg_price=Avg("price"))
            .order_by("date")
        )
        return {
            "name": name,
            "data": [
                [format_date_ddmmyyyy(w["date"]), format_price(w["avg_price"])]
                for w in weekly_prices
            ]
        }

    if params.get("district_id"):
        district_obj = qs.select_related("district").first()
        district_name = (
            district_obj.district.district_name_latin
            if district_obj else f"District {params['district_id']}"
        )
        series.append(generate_weekly_series(qs, district_name))

    elif params.get("region_id"):
        districts = District.objects.filter(
            district_id__in=qs.values_list("district__district_id", flat=True).distinct()
        )
        for district in districts:
            series.append(
                generate_weekly_series(
                    qs.filter(district__district_id=district.district_id),
                    district.district_name_latin
                )
            )

    else:
        regions = Region.objects.filter(
            region_id__in=qs.values_list("region__region_id", flat=True).distinct()
        )
        for region in regions:
            series.append(
                generate_weekly_series(
                    qs.filter(region__region_id=region.region_id),
                    region.region_name_latin
                )
            )

    return {
        "chart_type": "linegraph",
        "data": {
            "product_id": str(product_id),
            "weeks": WEEKS_IN_YEAR,
            "start_date": format_date_ddmmyyyy(start_date),
            "end_date": format_date_ddmmyyyy(end_date),
            "series": series,
        }
    }


def stacked_column_handler(qs, params):
    """
    Optimized handler for Highcharts stacked column chart showing regional price change contributions.
    - Uses ALL unique dates but ONLY returns non-zero contribution periods.
    - Filters by product_id (default: "Olma").
    - Includes separate totals per period.
    - Uses shared queryset (already filtered in dashboard_handler).
    """

    # Uzbek month names

    def format_display_date(date_obj):
        """Format date as '17 Dekabr, 2025'"""
        if not date_obj:
            return None
        return f"{date_obj.day} {MONTHS_UZ[date_obj.month]}, {date_obj.year}"

    def format_date_ddmmyyyy(date_obj):
        if not date_obj:
            return None
        return date_obj.strftime("%d.%m.%Y")

    def format_4dp(value):
        """Format to 4 decimal places"""
        return round(float(value), 4)

    # -------------------- PRODUCT HANDLING --------------------
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

    # -------------------- REGIONS --------------------
    regions = Region.objects.filter(
        region_id__in=product_qs.values_list("region__region_id", flat=True).distinct()
    ).order_by("region_name_latin")

    # -------------------- ALL UNIQUE DATES --------------------
    all_dates = list(product_qs.dates("date", "day").order_by("date"))
    if len(all_dates) < 2:
        return {
            "chart_type": "stacked_column",
            "data": [],
            "error": "Need at least 2 unique dates to calculate price changes"
        }

    # -------------------- SERIES INITIALIZATION --------------------
    series = [{"name": region.region_name_latin, "data": []} for region in regions]
    date_labels = []
    period_totals = []
    valid_period_contributions = []

    # -------------------- CONTRIBUTION CALCULATION --------------------
    for i, current_date in enumerate(all_dates[1:], 1):
        prev_date = all_dates[i - 1]

        # Current period averages
        current_period = product_qs.filter(date=current_date).values("region__region_id").annotate(
            avg_price=Avg("price")
        )
        current_prices = {item["region__region_id"]: item["avg_price"] or 0 for item in current_period}

        # Previous period averages
        prev_period = product_qs.filter(date=prev_date).values("region__region_id").annotate(
            avg_price=Avg("price")
        )
        prev_prices = {item["region__region_id"]: item["avg_price"] or 0 for item in prev_period}

        # Calculate contributions
        period_contributions = []
        period_total = 0.0

        for region in regions:
            current_price = current_prices.get(region.region_id, 0)
            prev_price = prev_prices.get(region.region_id, 0)

            if prev_price > 0:
                pct_change = (current_price / prev_price * 100 - 100)
                weight = float(getattr(region, "weights", 0))
                contribution = format_4dp(pct_change * weight)
            else:
                contribution = 0.0

            period_contributions.append(contribution)
            period_total += contribution

        # Only include non-zero periods
        if period_total != 0:
            valid_period_contributions.append(period_contributions)
            date_labels.append(format_date_ddmmyyyy(current_date))
            period_totals.append(format_4dp(period_total))

    # -------------------- POPULATE SERIES --------------------
    for j, region_series in enumerate(series):
        region_series["data"] = [contributions[j] for contributions in valid_period_contributions]

    if not date_labels:
        return {
            "chart_type": "stacked_column",
            "data": [],
            "error": "No significant price changes found"
        }

    # -------------------- RESPONSE --------------------
    return {
        "chart_type": "stacked_column",
        "data": {
            "product_id": str(product_id),
            "categories": date_labels,
            "series": series,
            "period_totals": period_totals,
            "total_regions": len(regions),
            "valid_periods": len(date_labels)
        }
    }


def global_metadata_handler(qs, params):
    from django.db.models import Max
    from datetime import datetime
    from .models import Product, Region, District

    # ✅ language comes from params (injected by DashboardAPIView)
    lang = params.get("lang", "uz")

    product_id = params.get("product_id")
    district_id = params.get("district_id")
    region_id = params.get("region_id")

    product_name = None
    region_name = None
    district_name = None

    LANG_FIELD_MAP = {
        "uz": "latin",
        "cy": "cyrillic",
        "ru": "russian",
        "en": "english",
    }

    def get_name(obj, prefix):
        field = f"{prefix}_name_{LANG_FIELD_MAP.get(lang, 'latin')}"
        return getattr(obj, field, None)

    # -------------------- AUTO-RESOLVE REGION FROM DISTRICT --------------------
    if district_id and not region_id:
        try:
            district = District.objects.select_related("region").get(district_id=district_id)
            district_name = get_name(district, "district")

            if district.region:
                region_id = district.region.region_id
                region_name = get_name(district.region, "region")
        except District.DoesNotExist:
            pass

    # -------------------- PRODUCT --------------------
    try:
        if product_id:
            product = Product.objects.get(product_id=product_id)
        else:
            product = Product.objects.get(product_name_latin="Olma")
            product_id = product.product_id

        product_name = get_name(product, "product")
    except Product.DoesNotExist:
        pass

    # -------------------- REGION --------------------
    if region_id and not region_name:
        try:
            region = Region.objects.get(region_id=region_id)
            region_name = get_name(region, "region")
        except Region.DoesNotExist:
            pass

    # -------------------- DISTRICT --------------------
    if district_id and not district_name:
        try:
            district = District.objects.get(district_id=district_id)
            district_name = get_name(district, "district")
        except District.DoesNotExist:
            pass

    # -------------------- FILTER QS --------------------
    product_qs = qs
    if product_id:
        product_qs = product_qs.filter(product__product_id=product_id)
    if region_id:
        product_qs = product_qs.filter(region__region_id=region_id)
    if district_id:
        product_qs = product_qs.filter(district__district_id=district_id)

    latest_date = product_qs.aggregate(latest=Max("date"))["latest"]
    active_date = params.get("date", latest_date)

    # -------------------- DATE FORMAT --------------------
    def format_display_date(date_value):
        if not date_value:
            return None

        if hasattr(date_value, "strftime"):
            date_obj = date_value
        else:
            date_obj = datetime.strptime(str(date_value), "%Y-%m-%d")

        return f"{date_obj.day} {MONTHS_BY_LANG[lang][date_obj.month]}, {date_obj.year}"

    # -------------------- FINAL RESPONSE --------------------
    return {
        "filters": {
            "product_id": str(product_id) if product_id else None,
            "district_id": str(district_id) if district_id else None,
            "region_id": str(region_id) if region_id else None,
            "date": str(active_date) if active_date else None,
        },
        "interface_text": {
            "product_name": product_name,
            "region_name": region_name,
            "district_name": district_name,
            "date_visual": format_display_date(active_date),
        },
        "date_options": list(
            product_qs.dates("date", "day").values_list("date", flat=True)
        ),
        "date_options_interface": [
            format_display_date(d)
            for d in product_qs.dates("date", "day").values_list("date", flat=True)
        ],
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
