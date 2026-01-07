from .models import *

def merge_price_observations(source, target, fk_field="product"):
    """
    Move observations from source to target, merging duplicates.
    fk_field: one of 'product', 'region', 'district'
    """
    qs = PriceObservation.objects.filter(**{fk_field: source})
    for obs in qs:
        lookup = {
            "district": obs.district,
            "product": target if fk_field == "product" else obs.product,
            "date": obs.date,
        }
        try:
            existing = PriceObservation.objects.get(**lookup)
            existing.price = obs.price
            existing.save()
            obs.delete()
        except PriceObservation.DoesNotExist:
            setattr(obs, fk_field, target)
            obs.save()
    source.delete()




def format_price(value: float) -> float:
    """Round price values to 2 decimals."""
    if value is None:
        return None
    return round(value, 2)

def format_price_change(value: float) -> float:
    """Round price change values to 4 decimals."""
    if value is None:
        return None
    return round(value, 4)
