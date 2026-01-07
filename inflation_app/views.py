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
        perm = UploadPermission.objects.prefetch_related('allowed_groups').get(code=code)
    except UploadPermission.DoesNotExist:
        messages.error(request, "Invalid upload code")
        return redirect('profile_page')

    if not request.user.groups.filter(id__in=perm.allowed_groups.values_list('id', flat=True)).exists():
        messages.error(request, "You do not have access to this upload section")
        return redirect('profile_page')

    # Database update logic
    try:
        upload_dir = os.path.join(settings.MEDIA_ROOT, perm.upload_path)

        # UPDATED: Look for BOTH old pattern AND new filename pattern
        files = (glob.glob(os.path.join(upload_dir, f"{code}_*")) +
                 glob.glob(os.path.join(upload_dir, f"{code}.*")))

        if files:
            updated_count = 0
            for file_path in files:
                filename = os.path.basename(file_path)
                # print(filename)
                # print(perm.code)
                if perm.code == "meta_data_upload":
                    updated_count += load_meta_data_fron_excel_file(file_path)
                if perm.code == 'inflation_data_1':
                    updated_count += load_price_data_from_excel_file(file_path)
                # Call specific processor based on perm.code
                # if perm.code == 'primary_sec':
                #     updated_count += process_primary_sec_file(file_path)
                # elif perm.code == 'issuance_projection':
                #     updated_count += issuance_forecast(file_path)

            messages.success(request, f"✅ Database updated! Processed {updated_count} files from {perm.label}")
        else:
            messages.warning(request, f"⚠️ No files found in {perm.upload_path}")

    except Exception as e:
        messages.error(request, f"❌ Update failed: {str(e)}")

    return redirect('profile_page')


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


class LatestPriceByProductAPIView(APIView, LoginRequiredMixin):
    """
    Returns latest average price by product,
    nominal change vs previous period,
    and percentage change.
    """

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

    def get_avg_prices_by_product(self, date):
        return (
            PriceObservation.objects
            .filter(date=date)
            .values("product_id", "product__product_name_latin")
            .annotate(avg_price=Avg("price"))
        )

    def get(self, request):
        latest_date = self.get_latest_date()
        if not latest_date:
            return Response([])

        previous_date = self.get_previous_date(latest_date)

        latest_prices = self.get_avg_prices_by_product(latest_date)

        previous_prices = {}
        if previous_date:
            previous_prices = {
                row["product_id"]: row["avg_price"]
                for row in self.get_avg_prices_by_product(previous_date)
            }

        response = []
        for row in latest_prices:
            product_id = row["product_id"]
            latest_price = row["avg_price"]
            prev_price = previous_prices.get(product_id)

            nominal_change = None
            percentage_change = None

            if prev_price is not None and prev_price != 0:
                nominal_change = latest_price - prev_price
                percentage_change = (nominal_change / prev_price) * 100

            response.append({
                "product_id": product_id,
                "product_name": row["product__product_name_latin"],
                "latest_price": round(latest_price, 2),
                "previous_price": round(prev_price, 2) if prev_price else None,
                "nominal_change": round(nominal_change, 2) if nominal_change else None,
                "percentage_change": round(percentage_change, 2) if percentage_change else None,
            })

        return Response(response)


class DashboardAPIView(APIView, LoginRequiredMixin):
    def get(self, request):
        qs = PriceObservation.objects.all()
        params = request.query_params

        result = {
            "global_metadata": None,  # Pre-initialize
            "charts": {}
        }

        # Execute ALL registered handlers
        for chart_key, handler in CHART_HANDLERS.items():
            try:
                chart_data = handler(qs, params)
                if chart_key == "global_metadata":
                    # Store global_metadata at top level ONLY
                    result["global_metadata"] = chart_data
                else:
                    # Other charts go to charts object
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
