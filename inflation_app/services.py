import pandas as pd
from django.conf import settings
from django.db import transaction
from django.core.cache import cache
from .models import Region, District, Product, PriceObservation, CPIData
import logging

logger = logging.getLogger(__name__)


@transaction.atomic
def load_meta_data_fron_excel_file(file_path):
    """
    Process reference Excel file → Region, District, Product models
    Atomic: if anything fails, nothing is saved.
    """
    processed = 0

    try:
        # ---------- REGIONS ----------
        region_df = pd.read_excel(file_path, sheet_name='regions')
        region_df = region_df.dropna(subset=['region_name'])

        for _, row in region_df.iterrows():
            defaults = {
                'region_name_cyrillic': str(row['region_name_cyrillic']).strip(),
                'hc_key': str(row['hc_key']).strip() if 'hc_key' in row and not pd.isna(row['hc_key']) else '',
            }

            # Optional language columns
            if 'region_name_russian' in row and not pd.isna(row['region_name_russian']):
                defaults['region_name_russian'] = str(row['region_name_russian']).strip()

            if 'region_name_english' in row and not pd.isna(row['region_name_english']):
                defaults['region_name_english'] = str(row['region_name_english']).strip()

            # Optional weights
            if 'weights' in row and not pd.isna(row['weights']):
                defaults['weights'] = row['weights']

            Region.objects.update_or_create(
                region_name_latin=str(row['region_name']).strip(),
                defaults=defaults
            )
            processed += 1

        # ---------- DISTRICTS ----------
        district_df = pd.read_excel(file_path, sheet_name='districts')
        district_df = district_df.dropna(subset=['district_name_latin'])

        for _, row in district_df.iterrows():
            defaults = {
                'district_name_cyrillic': str(row['district_name_cyrillic']).strip()
            }

            if 'district_name_russian' in row and not pd.isna(row['district_name_russian']):
                defaults['district_name_russian'] = str(row['district_name_russian']).strip()

            if 'district_name_english' in row and not pd.isna(row['district_name_english']):
                defaults['district_name_english'] = str(row['district_name_english']).strip()

            District.objects.update_or_create(
                district_name_latin=str(row['district_name_latin']).strip(),
                defaults=defaults
            )
            processed += 1

        # ---------- PRODUCTS ----------
        product_df = pd.read_excel(file_path, sheet_name='products')
        product_df = product_df.dropna(subset=['product_name_latin'])

        for _, row in product_df.iterrows():
            defaults = {
                'product_name_cyrillic': str(row['product_name_cyrillic']).strip()
            }

            if 'product_name_russian' in row and not pd.isna(row['product_name_russian']):
                defaults['product_name_russian'] = str(row['product_name_russian']).strip()

            if 'product_name_english' in row and not pd.isna(row['product_name_english']):
                defaults['product_name_english'] = str(row['product_name_english']).strip()

            Product.objects.update_or_create(
                product_name_latin=str(row['product_name_latin']).strip(),
                defaults=defaults
            )
            processed += 1

        print(f"✅ Processed {processed} reference records")
        return processed

    except Exception as e:
        print(f"❌ Reference file error: {e}")
        raise  # enforce rollback


def safe_delete_pattern(pattern: str):
    try:
        delete_func = getattr(cache, "delete_pattern", None)
        if callable(delete_func):
            delete_func(pattern)
    except Exception as e:
        logger.exception("Cache deletion failed: %s", e)


@transaction.atomic
def load_price_data_from_excel_file(file_path):
    """
    Load price data from Excel into PriceObservation.
    """

    def norm(val):
        return str(val).strip().lower()

    try:
        price_df = pd.read_excel(file_path, sheet_name="prices")
        price_df = price_df.dropna(
            subset=["region_name", "district_name", "product", "date", "price"]
        )
        price_df["date"] = pd.to_datetime(price_df["date"]).dt.date

        # Prefetch metadata
        regions_map = {
            norm(n): r
            for r in Region.objects.all()
            for n in (r.region_name_latin, r.region_name_cyrillic)
            if n
        }
        districts_map = {
            norm(n): d
            for d in District.objects.all()
            for n in (d.district_name_latin, d.district_name_cyrillic)
            if n
        }
        products_map = {
            norm(n): p
            for p in Product.objects.all()
            for n in (p.product_name_latin, p.product_name_cyrillic)
            if n
        }

        new_regions, new_districts, new_products = {}, {}, {}

        for _, row in price_df.iterrows():
            r_key = norm(row["region_name"])
            d_key = norm(row["district_name"])
            p_key = norm(row["product"])

            if r_key not in regions_map and r_key not in new_regions:
                new_regions[r_key] = Region(
                    region_name_latin=row["region_name"].strip(),
                    region_name_cyrillic="",
                    hc_key="",
                    weights=None,
                )

            if d_key not in districts_map and d_key not in new_districts:
                new_districts[d_key] = District(
                    district_name_latin=row["district_name"].strip(),
                    district_name_cyrillic="",
                )

            if p_key not in products_map and p_key not in new_products:
                new_products[p_key] = Product(
                    product_name_latin=row["product"].strip(),
                    product_name_cyrillic="",
                )

        if new_regions:
            Region.objects.bulk_create(new_regions.values())
        if new_districts:
            District.objects.bulk_create(new_districts.values())
        if new_products:
            Product.objects.bulk_create(new_products.values())

        # Reload metadata
        regions_map = {
            norm(n): r
            for r in Region.objects.all()
            for n in (r.region_name_latin, r.region_name_cyrillic)
            if n
        }
        districts_map = {
            norm(n): d
            for d in District.objects.all()
            for n in (d.district_name_latin, d.district_name_cyrillic)
            if n
        }
        products_map = {
            norm(n): p
            for p in Product.objects.all()
            for n in (p.product_name_latin, p.product_name_cyrillic)
            if n
        }

        price_data = []
        for _, row in price_df.iterrows():
            r_key = norm(row["region_name"])
            d_key = norm(row["district_name"])
            p_key = norm(row["product"])

            try:
                region = regions_map[r_key]
                district = districts_map[d_key]
                product = products_map[p_key]
            except KeyError as e:
                raise ValueError(f"Missing FK metadata for {e}")

            price_data.append({
                "region_id": region.region_id,
                "district_id": district.district_id,
                "product_id": product.product_id,
                "date": row["date"],
                "price": float(row["price"]),
            })

        # Bulk upsert
        if hasattr(PriceObservation.objects, "bulk_upsert"):
            PriceObservation.objects.bulk_upsert(
                price_data,
                unique_fields=["district_id", "product_id", "date"],
                update_fields=["price", "region_id"],
                batch_size=1000,
            )
        else:
            incoming_map = {
                (d["district_id"], d["product_id"], d["date"]): d
                for d in price_data
            }
            existing = PriceObservation.objects.filter(
                district_id__in=[k[0] for k in incoming_map],
                product_id__in=[k[1] for k in incoming_map],
                date__in=[k[2] for k in incoming_map],
            )
            existing_map = {
                (o.district_id, o.product_id, o.date): o
                for o in existing
            }
            to_create, to_update = [], []
            for key, data in incoming_map.items():
                if key in existing_map:
                    obj = existing_map[key]
                    obj.price = data["price"]
                    obj.region_id = data["region_id"]
                    to_update.append(obj)
                else:
                    to_create.append(PriceObservation(**data))

            if to_create:
                PriceObservation.objects.bulk_create(to_create, batch_size=1000)
            if to_update:
                PriceObservation.objects.bulk_update(to_update, ["price", "region_id"], batch_size=1000)

        # ---------- SAFE CACHE INVALIDATION ----------
        transaction.on_commit(lambda: safe_delete_pattern("dashboard:*"))

        return len(price_data)

    except Exception as e:
        logger.exception("Error loading price data from Excel: %s", file_path)
        raise


@transaction.atomic
def load_cpi_data_from_excel_file(file_path):
    """
    Load CPI data from Excel into CPIData.
    """

    def norm(val):
        return str(val).strip().lower()

    try:
        cpi_df = pd.read_excel(file_path, sheet_name="cpi")
        cpi_df = cpi_df.dropna(
            subset=["product", "year", "month", "weight", "price_change"]
        )
        cpi_df["year"] = cpi_df["year"].astype(int)
        cpi_df["month"] = cpi_df["month"].astype(int)
        cpi_df["weight"] = cpi_df["weight"].astype(float)
        cpi_df["price_change"] = cpi_df["price_change"].astype(float)

        # Prefetch metadata
        products_map = {
            norm(n): p
            for p in Product.objects.all()
            for n in (p.product_name_latin, p.product_name_cyrillic)
            if n
        }

        new_products = {}

        for _, row in cpi_df.iterrows():
            p_key = norm(row["product"])

            if p_key not in products_map and p_key not in new_products:
                new_products[p_key] = Product(
                    product_name_latin=row["product"].strip(),
                    product_name_cyrillic="",
                )

        if new_products:
            Product.objects.bulk_create(new_products.values())

        # Reload metadata
        products_map = {
            norm(n): p
            for p in Product.objects.all()
            for n in (p.product_name_latin, p.product_name_cyrillic)
            if n
        }

        cpi_data = []
        for _, row in cpi_df.iterrows():
            p_key = norm(row["product"])

            try:
                product = products_map[p_key]
            except KeyError as e:
                raise ValueError(f"Missing product metadata for {e}")

            cpi_data.append({
                "product_id": product.product_id,
                "year": row["year"],
                "month": row["month"],
                "weight": row["weight"],
                "price_change": row["price_change"],
            })

        # Bulk upsert
        if hasattr(CPIData.objects, "bulk_upsert"):
            CPIData.objects.bulk_upsert(
                cpi_data,
                unique_fields=["product_id", "year", "month"],
                update_fields=["weight", "price_change"],
                batch_size=1000,
            )
        else:
            incoming_map = {
                (d["product_id"], d["year"], d["month"]): d
                for d in cpi_data
            }
            existing = CPIData.objects.filter(
                product_id__in=[k[0] for k in incoming_map],
                year__in=[k[1] for k in incoming_map],
                month__in=[k[2] for k in incoming_map],
            )
            existing_map = {
                (o.product_id, o.year, o.month): o
                for o in existing
            }
            to_create, to_update = [], []
            for key, data in incoming_map.items():
                if key in existing_map:
                    obj = existing_map[key]
                    obj.weight = data["weight"]
                    obj.price_change = data["price_change"]
                    to_update.append(obj)
                else:
                    to_create.append(CPIData(**data))

            if to_create:
                CPIData.objects.bulk_create(to_create, batch_size=1000)
            if to_update:
                CPIData.objects.bulk_update(to_update, ["weight", "price_change"], batch_size=1000)

        # ---------- SAFE CACHE INVALIDATION ----------
        transaction.on_commit(lambda: safe_delete_pattern("dashboard:*"))

        return len(cpi_data)

    except Exception as e:
        logger.exception("Error loading CPI data from Excel: %s", file_path)
        raise
