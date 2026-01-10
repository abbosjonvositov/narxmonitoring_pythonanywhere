from .models import *
from django.views.generic import TemplateView
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import UploadPermission
from .services import *
from django.contrib import messages
from django.shortcuts import redirect
import os
import glob
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Max
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import PriceObservation
from .handlers import CHART_HANDLERS


# Create your views here.
class LandingPageView(LoginRequiredMixin, TemplateView):
    template_name = "landing_page.html"
    login_url = '/login/'


class ProfilePageView(TemplateView, LoginRequiredMixin):
    template_name = "profile_page.html"
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Existing profile logic
        user_profile = UserProfile.objects.select_related(
            "organization", "position"
        ).filter(user=self.request.user).first()

        if user_profile:
            context["profile"] = {
                "user": user_profile.user,
                "organization": user_profile.organization,
                "position": user_profile.position,
                "mobile_contacts": user_profile.mobile_contacts,
                "corporate_contacts": user_profile.corporate_contacts,
                "department": user_profile.department,
                "subdivision": user_profile.subdivision,
                "profile_picture": user_profile.profile_picture.url if user_profile.profile_picture else None,
            }
        else:
            context["profile"] = None

        # NEW: Filter UploadPermissions user can access
        all_perms = UploadPermission.objects.prefetch_related('allowed_groups').all()
        authorized_perms = [
            perm for perm in all_perms
            if self.request.user.groups.filter(
                id__in=perm.allowed_groups.values_list('id', flat=True)
            ).exists()
        ]
        context["authorized_perms"] = authorized_perms  # Admin in cbu_team sees these

        return context


@login_required
def upload_view(request, code):
    try:
        perm = UploadPermission.objects.prefetch_related('allowed_groups').get(code=code)
    except UploadPermission.DoesNotExist:
        messages.error(request, "Invalid upload code")
        return redirect('profile_page')

    if not request.user.groups.filter(id__in=perm.allowed_groups.values_list('id', flat=True)).exists():
        messages.error(request, "You do not have access to this upload section")
        return redirect('profile_page')

    if request.method == 'POST':
        if "upload" in request.POST:
            file = request.FILES.get('file')
            if file:
                upload_dir = os.path.join(settings.MEDIA_ROOT, perm.upload_path)
                os.makedirs(upload_dir, exist_ok=True)

                # CHANGE: Rename file to just the code (removes original filename)
                file_path = os.path.join(upload_dir, f"{code}{os.path.splitext(file.name)[1]}")

                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)

                messages.success(request, f"✅ File uploaded as: {os.path.basename(file_path)}")
            else:
                messages.warning(request, "❌ No file selected")

    return redirect('profile_page')


@login_required
def update_view(request, code):
    try:
        perm = UploadPermission.objects.prefetch_related("allowed_groups").get(code=code)
    except UploadPermission.DoesNotExist:
        messages.error(request, "Invalid upload code")
        return redirect("profile_page")

    if not request.user.groups.filter(
            id__in=perm.allowed_groups.values_list("id", flat=True)
    ).exists():
        messages.error(request, "You do not have access to this upload section")
        return redirect("profile_page")

    try:
        upload_dir = os.path.join(settings.MEDIA_ROOT, perm.upload_path)

        files = (
                glob.glob(os.path.join(upload_dir, f"{code}_*"))
                + glob.glob(os.path.join(upload_dir, f"{code}.*"))
        )

        if not files:
            messages.warning(request, f"⚠️ No files found in {perm.upload_path}")
            return redirect("profile_page")

        total_rows = 0
        processed_files = 0

        for file_path in files:
            if perm.code == "meta_data_upload":
                rows = load_meta_data_fron_excel_file(file_path)

            elif perm.code == "inflation_data_1":
                rows = load_price_data_from_excel_file(file_path)

            else:
                raise ValueError(f"No processor defined for code '{perm.code}'")

            total_rows += rows
            processed_files += 1

        messages.success(
            request,
            f"✅ Database updated! "
            f"{processed_files} file(s), {total_rows} row(s) processed."
        )

    except Exception as e:
        # IMPORTANT: debugger + traceback visibility
        if settings.DEBUG:
            import pdb;
            pdb.set_trace()
        messages.error(request, f"❌ Update failed: {e}")
        raise  # <- optional but recommended in dev

    return redirect("profile_page")


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('landing_page')  # Replace with your desired redirect URL name
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})


class LogoutView(View, LoginRequiredMixin):
    def get(self, request):
        logout(request)
        return redirect('login')

    def post(self, request):
        logout(request)
        return redirect('login')


class LatestPriceByProductAPIView(LoginRequiredMixin, APIView):
    """
    Returns latest average price by product,
    nominal change vs previous period,
    percentage change,
    with product name localized by LANGUAGE_CODE.
    """

    LANG_FIELD_MAP = {
        "uz": "product_name_latin",
        "cy": "product_name_cyrillic",
        "ru": "product_name_russian",
        "en": "product_name_english",
    }

    def get_latest_date(self):
        return PriceObservation.objects.aggregate(
            latest=Max("date")
        )["latest"]

    def get_previous_date(self, latest_date):
        return (
            PriceObservation.objects
            .filter(date__lt=latest_date)
            .aggregate(prev=Max("date"))
            ["prev"]
        )

    def get_avg_prices_by_product(self, date, name_field):
        return (
            PriceObservation.objects
            .filter(date=date)
            .values(
                "product_id",
                f"product__{name_field}"
            )
            .annotate(avg_price=Avg("price"))
        )

    def get(self, request):
        lang = request.LANGUAGE_CODE or "uz"
        name_field = self.LANG_FIELD_MAP.get(lang, "product_name_latin")

        latest_date = self.get_latest_date()
        if not latest_date:
            return Response([])

        previous_date = self.get_previous_date(latest_date)

        latest_prices = self.get_avg_prices_by_product(latest_date, name_field)

        previous_prices = {}
        if previous_date:
            previous_prices = {
                row["product_id"]: row["avg_price"]
                for row in self.get_avg_prices_by_product(previous_date, name_field)
            }

        response = []

        for row in latest_prices:
            product_id = row["product_id"]
            latest_price = row["avg_price"]
            prev_price = previous_prices.get(product_id)

            # ----- CHANGE CALCULATIONS -----
            nominal_change = (
                latest_price - prev_price
                if prev_price is not None
                else 0
            )

            percentage_change = (
                (nominal_change / prev_price) * 100
                if prev_price not in (None, 0)
                else 0
            )

            response.append({
                "product_id": product_id,
                "product_name": row.get(f"product__{name_field}"),
                "latest_price": round(latest_price, 2),
                "previous_price": round(prev_price, 2) if prev_price is not None else None,
                "nominal_change": round(nominal_change, 2),
                "percentage_change": round(percentage_change, 2),
            })

        return Response(response)


class DashboardAPIView(APIView, LoginRequiredMixin):
    def get(self, request):
        qs = PriceObservation.objects.all()

        params = request.query_params.copy()
        params["lang"] = request.LANGUAGE_CODE  # ✅ inject language

        result = {
            "global_metadata": None,
            "charts": {}
        }

        for chart_key, handler in CHART_HANDLERS.items():
            try:
                chart_data = handler(qs, params)
                if chart_key == "global_metadata":
                    result["global_metadata"] = chart_data
                else:
                    result["charts"][chart_key] = chart_data
            except Exception as e:
                if chart_key == "global_metadata":
                    result["global_metadata"] = {"error": f"Metadata unavailable: {str(e)}"}
                else:
                    result["charts"][chart_key] = {
                        "error": f"Chart unavailable: {str(e)}",
                        "chart_type": chart_key
                    }

        return Response(result)


from django.db.models import Avg, Max
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response


def calculate_change(latest, prev):
    """
    Return nominal and percentage change between latest and prev.
    """
    if prev is None or prev == 0:
        return {"nominal": None, "pct": None}
    return {
        "nominal": round(latest - prev, 2),
        "pct": round(((latest - prev) / prev) * 100, 2)
    }


def get_change_by_offset(product, region=None, offset=1):
    """
    Compare latest avg price vs N-th previous avg price.
    offset=1 → 1W
    offset=4 → 1M
    offset=12 → 3M
    offset=24 → 6M
    offset=52 → 1Y
    """
    qs = PriceObservation.objects.filter(product=product)
    if region:
        qs = qs.filter(region=region)

    qs = (
        qs.values("date")
        .annotate(avg_price=Avg("price"))
        .order_by("-date")
    )

    prices = list(qs)
    if len(prices) <= offset:
        return {"nominal": None, "pct": None}

    latest_price = prices[0]["avg_price"]
    past_price = prices[offset]["avg_price"]

    return calculate_change(latest_price, past_price)


class ProductPerformanceView(APIView):
    def get(self, request):
        # --- Step 0: determine language ---
        lang = getattr(request, "LANGUAGE_CODE", "uz")
        LANG_FIELD_MAP = {
            "uz": "latin",
            "cy": "cyrillic",
            "ru": "russian",
            "en": "english",
        }
        name_field = f"product_name_{LANG_FIELD_MAP.get(lang, 'latin')}"

        # --- Step 1: find latest observation date in DB ---
        latest_date = PriceObservation.objects.aggregate(max_date=Max("date"))["max_date"]

        # --- Step 2: check cache (language-aware) ---
        cache_key = f"products_performance_{lang}"
        cached = cache.get(cache_key)
        if cached and cached.get("latest_date") == latest_date:
            return Response({"products": cached["data"]})

        # --- Step 3: recompute fresh data ---
        products_data = []

        for product in Product.objects.all():
            product_name = getattr(product, name_field, product.product_name_latin)

            qs = (
                PriceObservation.objects.filter(product=product)
                .values("date")
                .annotate(avg_price=Avg("price"))
                .order_by("-date")
            )
            if not qs.exists():
                continue

            latest_obs = qs[0]
            prev_obs = qs[1] if len(qs) > 1 else None

            latest_price = latest_obs["avg_price"]
            prev_price = prev_obs["avg_price"] if prev_obs else None
            change_info = calculate_change(latest_price, prev_price)

            product_data = {
                "product_id": product.product_id,
                "name": product_name,
                "price": round(latest_price, 2),
                "prevPrice": round(prev_price, 2) if prev_price else None,
                "change": change_info,
                "performance": [
                    {"period": "1W", "change": get_change_by_offset(product, offset=1)},
                    {"period": "1M", "change": get_change_by_offset(product, offset=4)},
                    {"period": "3M", "change": get_change_by_offset(product, offset=12)},
                    {"period": "6M", "change": get_change_by_offset(product, offset=24)},
                    {"period": "YTD", "change": get_change_by_offset(product, offset=len(qs) - 1)},
                    {"period": "1Y", "change": get_change_by_offset(product, offset=52)},
                ],
                "regions": []
            }

            # Region-level performance
            for region in Region.objects.all():
                region_name_field = f"region_name_{LANG_FIELD_MAP.get(lang, 'latin')}"
                region_name = getattr(region, region_name_field, region.region_name_latin)

                qs_region = (
                    PriceObservation.objects.filter(product=product, region=region)
                    .values("date")
                    .annotate(avg_price=Avg("price"))
                    .order_by("-date")
                )

                if not qs_region.exists():
                    continue

                latest_region_obs = qs_region[0]
                prev_region_obs = qs_region[1] if len(qs_region) > 1 else None

                latest_region_price = latest_region_obs["avg_price"]
                prev_region_price = prev_region_obs["avg_price"] if prev_region_obs else None
                region_change_info = calculate_change(latest_region_price, prev_region_price)

                region_data = {
                    "name": region_name,
                    "price": round(latest_region_price, 2),
                    "prevPrice": round(prev_region_price, 2) if prev_region_price else None,
                    "change": region_change_info,
                    "performance": [
                        {"period": "1W", "change": get_change_by_offset(product, region=region, offset=1)},
                        {"period": "1M", "change": get_change_by_offset(product, region=region, offset=4)},
                        {"period": "3M", "change": get_change_by_offset(product, region=region, offset=12)},
                        {"period": "6M", "change": get_change_by_offset(product, region=region, offset=24)},
                        {"period": "YTD",
                         "change": get_change_by_offset(product, region=region, offset=len(qs_region) - 1)},
                        {"period": "1Y", "change": get_change_by_offset(product, region=region, offset=52)},
                    ]
                }
                product_data["regions"].append(region_data)

            products_data.append(product_data)

        # --- Step 4: update cache (language-aware) ---
        cache.set(cache_key, {
            "latest_date": latest_date,
            "data": products_data
        }, timeout=None)

        return Response({"products": products_data})
