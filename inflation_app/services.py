import pandas as pd
from django.db import transaction
from .models import *
from django.db import transaction
from django.db.models import Q


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
                'hc_key': str(row['hc_key']).strip() if 'hc_key' in row and not pd.isna(row['hc_key']) else ''
            }

            # Add weights safely (handles NaN/null values)
            if 'weights' in row and not pd.isna(row['weights']):
                defaults['weights'] = row['weights']  # DecimalField handles float/decimal conversion
            # else: weights remains None/null (doesn't overwrite existing values)

            Region.objects.update_or_create(
                region_name_latin=str(row['region_name']).strip(),
                defaults=defaults
            )
            processed += 1

        # ---------- DISTRICTS ----------
        district_df = pd.read_excel(file_path, sheet_name='districts')
        district_df = district_df.dropna(subset=['district_name_latin'])

        for _, row in district_df.iterrows():
            District.objects.update_or_create(
                district_name_latin=str(row['district_name_latin']).strip(),
                defaults={
                    'district_name_cyrillic': str(row['district_name_cyrillic']).strip()
                }
            )
            processed += 1

        # ---------- PRODUCTS ----------
        product_df = pd.read_excel(file_path, sheet_name='products')
        product_df = product_df.dropna(subset=['product_name_latin'])

        for _, row in product_df.iterrows():
            Product.objects.update_or_create(
                product_name_latin=str(row['product_name_latin']).strip(),
                defaults={
                    'product_name_cyrillic': str(row['product_name_cyrillic']).strip()
                }
            )
            processed += 1

        print(f"✅ Processed {processed} reference records")
        return processed

    except Exception as e:
        # Any exception triggers full rollback because of @transaction.atomic
        print(f"Reference file error: {e}")
        raise  # IMPORTANT: re-raise to enforce rollback



@transaction.atomic
def load_price_data_from_excel_file(file_path):
    """
    Load price data from Excel into PriceObservation.

    - Auto-creates Region, District, Product if missing
    - Fully atomic
    - Optimized for large files (~30K rows)
    - Safe bulk upsert logic
    """
    processed = 0

    # ---------- READ EXCEL ----------
    price_df = pd.read_excel(file_path, sheet_name="prices")
    price_df = price_df.dropna(subset=["region_name", "district_name", "product", "date", "price"])
    price_df["date"] = pd.to_datetime(price_df["date"]).dt.date

    # ---------- PREFETCH EXISTING DIMENSIONS ----------
    regions_map = {n.lower(): r for r in Region.objects.all()
                   for n in [r.region_name_latin, r.region_name_cyrillic] if n}
    districts_map = {n.lower(): d for d in District.objects.all()
                     for n in [d.district_name_latin, d.district_name_cyrillic] if n}
    products_map = {n.lower(): p for p in Product.objects.all()
                    for n in [p.product_name_latin, p.product_name_cyrillic] if n}

    new_regions = []
    new_districts = []
    new_products = []

    # ---------- COLLECT NEW DIMENSIONS ----------
    for _, row in price_df.iterrows():
        # Region
        region_name = str(row["region_name"]).strip()
        region_key = region_name.lower()
        if region_key not in regions_map:
            new_regions.append(Region(region_name_latin=region_name, region_name_cyrillic="", hc_key="", weights=None))
            regions_map[region_key] = None  # placeholder

        # District
        district_name = str(row["district_name"]).strip()
        district_key = district_name.lower()
        if district_key not in districts_map:
            new_districts.append(District(district_name_latin=district_name, district_name_cyrillic=""))
            districts_map[district_key] = None

        # Product
        product_name = str(row["product"]).strip()
        product_key = product_name.lower()
        if product_key not in products_map:
            new_products.append(Product(product_name_latin=product_name, product_name_cyrillic=""))
            products_map[product_key] = None

    # ---------- BULK CREATE DIMENSIONS ----------
    if new_regions:
        Region.objects.bulk_create(new_regions)
    if new_districts:
        District.objects.bulk_create(new_districts)
    if new_products:
        Product.objects.bulk_create(new_products)

    # ---------- RELOAD DIMENSIONS TO ENSURE PKs ----------
    regions_map = {n.lower(): r for r in Region.objects.all()
                   for n in [r.region_name_latin, r.region_name_cyrillic] if n}
    districts_map = {n.lower(): d for d in District.objects.all()
                     for n in [d.district_name_latin, d.district_name_cyrillic] if n}
    products_map = {n.lower(): p for p in Product.objects.all()
                    for n in [p.product_name_latin, p.product_name_cyrillic] if n}

    # ---------- PREPARE PRICE DATA ----------
    price_data = []
    for _, row in price_df.iterrows():
        region = regions_map[row["region_name"].strip().lower()]
        district = districts_map[row["district_name"].strip().lower()]
        product = products_map[row["product"].strip().lower()]

        price_data.append({
            "region_id": region.region_id,
            "district_id": district.district_id,
            "product_id": product.product_id,
            "date": row["date"],
            "price": float(row["price"]),
        })

    # ---------- FAST PATH: DJANGO 5.0+ ----------
    if hasattr(PriceObservation.objects, "bulk_upsert"):
        PriceObservation.objects.bulk_upsert(
            price_data,
            unique_fields=["district_id", "product_id", "date"],
            update_fields=["price", "region_id"],
            batch_size=1000,
        )
        return len(price_data)

    # ---------- UNIVERSAL FALLBACK (SAFE) ----------
    # Build map of incoming data
    incoming_map = {(d["district_id"], d["product_id"], d["date"]): d for d in price_data}

    # Fetch existing rows
    existing_objects = list(
        PriceObservation.objects.filter(
            district_id__in=[k[0] for k in incoming_map.keys()],
            product_id__in=[k[1] for k in incoming_map.keys()],
            date__in=[k[2] for k in incoming_map.keys()],
        )
    )
    existing_map = {(o.district_id, o.product_id, o.date): o for o in existing_objects}

    to_create = []
    to_update = []

    for key, data in incoming_map.items():
        if key in existing_map:
            obj = existing_map[key]
            obj.price = data["price"]
            obj.region_id = data["region_id"]
            to_update.append(obj)
        else:
            to_create.append(PriceObservation(**data))

    # Bulk create new rows
    if to_create:
        PriceObservation.objects.bulk_create(to_create, batch_size=1000)

    # Bulk update existing rows
    if to_update:
        PriceObservation.objects.bulk_update(to_update, ["price", "region"], batch_size=1000)

    return len(price_data)

