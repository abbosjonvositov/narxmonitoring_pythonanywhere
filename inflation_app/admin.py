from .models import *
from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from .forms import *


@admin.register(UploadPermission)
class UploadPermissionAdmin(admin.ModelAdmin):
    list_display = ('label', 'code', 'upload_path', 'get_allowed_groups')
    list_filter = ('code',)
    search_fields = ('code', 'label')

    def get_allowed_groups(self, obj):
        return ", ".join([group.name for group in obj.allowed_groups.all()])

    get_allowed_groups.short_description = 'Allowed Groups'


from django.contrib import admin
from django.contrib import messages
from django.db import connection, transaction
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from django.core.management.color import no_style
from django.db import connection, transaction
from django.contrib import messages


def flush_and_reset(modeladmin, request, queryset):
    """
    Universal flush + ID reset action for any supported DB backend.
    Deletes all rows in the queryset's model table and resets the PK sequence.
    """
    count = queryset.count()
    table_name = modeladmin.model._meta.db_table

    # Delete all rows
    queryset.delete()

    # Reset the sequence using Django's sequence_reset_sql (works across DBs)
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), [modeladmin.model])
    if sequence_sql:
        with connection.cursor() as cursor:
            for sql in sequence_sql:
                cursor.execute(sql)

    modeladmin.message_user(
        request,
        f"✅ Flushed {count} {modeladmin.model.__name__}. Table empty. Next ID reset.",
        level=messages.SUCCESS
    )


flush_and_reset.short_description = "⚠️ FLUSH ALL & RESET ID (irreversible!)"


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("region_id", "region_name_latin", "region_name_cyrillic", "weights")
    search_fields = ("region_name_latin", "region_name_cyrillic")
    actions = [flush_and_reset]  # ✅ Added flush action

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/replace/",
                self.admin_site.admin_view(self.replace_region_view),
                name="inflation_app_region_replace",
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        extra_context["original"] = obj
        return super().change_view(request, object_id, form_url, extra_context)

    def replace_region_view(self, request, object_id):
        region_to_remove = get_object_or_404(Region, pk=object_id)

        if request.method == "POST":
            form = ReplaceRegionForm(
                request.POST,
                queryset=Region.objects.exclude(pk=region_to_remove.pk),
            )
            if form.is_valid():
                target = form.cleaned_data["target_region"]
                with transaction.atomic():
                    updated = PriceObservation.objects.filter(
                        region=region_to_remove
                    ).update(region=target)
                    region_to_remove.delete()
                messages.success(
                    request,
                    f"{updated} price records moved. Region replaced successfully.",
                )
                return redirect(reverse("admin:inflation_app_region_changelist"))
        else:
            form = ReplaceRegionForm(
                queryset=Region.objects.exclude(pk=region_to_remove.pk)
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Replace region",
            "form": form,
            "region": region_to_remove,
            "opts": Region._meta,
            "original": region_to_remove,
            "app_label": Region._meta.app_label,
        }
        return render(
            request,
            "admin/inflation_app/region/replace_region.html",
            context,
        )


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("district_id", "district_name_latin", "district_name_cyrillic")
    search_fields = ("district_name_latin", "district_name_cyrillic")
    actions = [flush_and_reset]  # ✅ Added flush action

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/replace/",
                self.admin_site.admin_view(self.replace_district_view),
                name="inflation_app_district_replace",
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        extra_context["original"] = obj
        return super().change_view(request, object_id, form_url, extra_context)

    def replace_district_view(self, request, object_id):
        district_to_remove = get_object_or_404(District, pk=object_id)

        if request.method == "POST":
            form = ReplaceDistrictForm(
                request.POST,
                queryset=District.objects.exclude(pk=district_to_remove.pk),
            )
            if form.is_valid():
                target = form.cleaned_data["target_district"]

                if target.pk == district_to_remove.pk:
                    messages.error(request, "Cannot replace with itself.")
                else:
                    with transaction.atomic():
                        updated_count = 0
                        for obs in PriceObservation.objects.filter(district=district_to_remove):
                            try:
                                existing = PriceObservation.objects.get(
                                    district=target,
                                    product=obs.product,
                                    date=obs.date,
                                )
                                existing.price = obs.price
                                existing.save()
                                obs.delete()
                            except PriceObservation.DoesNotExist:
                                obs.district = target
                                obs.save()
                            updated_count += 1

                        district_to_remove.delete()

                    messages.success(
                        request,
                        f"{updated_count} price records moved/merged. District replaced successfully.",
                    )
                    return redirect(reverse("admin:inflation_app_district_changelist"))
        else:
            form = ReplaceDistrictForm(
                queryset=District.objects.exclude(pk=district_to_remove.pk)
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Replace district",
            "form": form,
            "district": district_to_remove,
            "opts": District._meta,
            "original": district_to_remove,
            "app_label": District._meta.app_label,
        }
        return render(
            request,
            "admin/inflation_app/district/replace_district.html",
            context,
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "product_name_latin", "product_name_cyrillic")
    search_fields = ("product_name_latin", "product_name_cyrillic")
    actions = [flush_and_reset]  # ✅ Added flush action

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/replace/",
                self.admin_site.admin_view(self.replace_product_view),
                name="inflation_app_product_replace",
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        extra_context["original"] = obj
        return super().change_view(request, object_id, form_url, extra_context)

    def replace_product_view(self, request, object_id):
        if not self.has_change_permission(request):
            messages.error(request, _("You do not have permission to replace products."))
            return redirect(reverse("admin:inflation_app_product_changelist"))

        product_to_remove = get_object_or_404(Product, pk=object_id)

        if request.method == "POST":
            form = ReplaceProductForm(
                request.POST,
                queryset=Product.objects.exclude(pk=product_to_remove.pk),
            )
            if form.is_valid():
                target = form.cleaned_data["target_product"]

                if target.pk == product_to_remove.pk:
                    messages.error(request, _("Cannot replace with itself."))
                else:
                    with transaction.atomic():
                        updated_count = 0
                        for obs in PriceObservation.objects.filter(product=product_to_remove):
                            try:
                                existing = PriceObservation.objects.get(
                                    district=obs.district,
                                    product=target,
                                    date=obs.date,
                                )
                                existing.price = obs.price
                                existing.save()
                                obs.delete()
                            except PriceObservation.DoesNotExist:
                                obs.product = target
                                obs.save()
                            updated_count += 1

                        product_to_remove.delete()

                    messages.success(
                        request,
                        _("%(count)d price records moved/merged. Product replaced successfully.")
                        % {"count": updated_count},
                    )
                    return redirect(reverse("admin:inflation_app_product_changelist"))
        else:
            form = ReplaceProductForm(
                queryset=Product.objects.exclude(pk=product_to_remove.pk)
            )

        context = {
            **self.admin_site.each_context(request),
            "title": _("Replace product"),
            "form": form,
            "product": product_to_remove,
            "opts": Product._meta,
            "original": product_to_remove,
            "app_label": Product._meta.app_label,
        }
        return render(
            request,
            "admin/inflation_app/product/replace_product.html",
            context,
        )
