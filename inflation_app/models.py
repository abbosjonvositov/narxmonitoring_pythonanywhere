from django.db import models
from django.contrib.auth.models import Group, User
import os


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'user_organization'


class Position(models.Model):
    title = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'user_position'


def user_profile_picture_path(instance, filename):
    # This will create: MEDIA_ROOT/profile_pics/<username>/profile_img.<ext>
    ext = filename.split('.')[-1]
    filename = f"profile_img.{ext}"
    return os.path.join('profile_pics', instance.user.username, filename)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # New Fields
    mobile_contacts = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="User's mobile phone number(s)"
    )
    corporate_contacts = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Corporate contact details (email or phone)"
    )
    department = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Department name"
    )
    subdivision = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Subdivision or section"
    )

    # Existing Fields
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='profiles'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='profiles'
    )

    profile_picture = models.ImageField(
        upload_to=user_profile_picture_path,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username}'s profile"


class UploadPermission(models.Model):
    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Internal code, ex: 'bond_portfolio', 'market_rates'"
    )
    label = models.CharField(
        max_length=200,
        help_text="Shown in UI, ex: 'Bond Portfolio Upload'"
    )
    allowed_groups = models.ManyToManyField(Group)

    upload_path = models.CharField(
        max_length=255,
        help_text="Directory where the files will be uploaded, ex: 'bond/'"
    )

    class Meta:
        permissions = [
            ("can_upload_{code}", "Can upload files for {label}"),
        ]

    def __str__(self):
        return self.label


# Create your models here.
class Region(models.Model):
    region_id = models.AutoField(primary_key=True)
    region_name_cyrillic = models.CharField(max_length=255)
    region_name_latin = models.CharField(max_length=255)
    hc_key = models.CharField(max_length=255)
    weights = models.DecimalField(
        max_digits=12,
        decimal_places=6,  # High precision to preserve all decimal places
        null=True,
        blank=True
    )

    class Meta:
        db_table = "region"
        verbose_name = "Region"
        verbose_name_plural = "Regions"

    def __str__(self):
        return self.region_name_latin


class District(models.Model):
    district_id = models.AutoField(primary_key=True)
    district_name_cyrillic = models.CharField(max_length=255)
    district_name_latin = models.CharField(max_length=255)

    class Meta:
        db_table = "district"
        verbose_name = "District"
        verbose_name_plural = "Districts"

    def __str__(self):
        return self.district_name_latin


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_name_cyrillic = models.CharField(max_length=255)
    product_name_latin = models.CharField(max_length=255)

    class Meta:
        db_table = "product"
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.product_name_latin


class PriceObservation(models.Model):
    id = models.AutoField(primary_key=True)

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="price_observations"
    )

    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name="price_observations"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="price_observations"
    )

    date = models.DateField()
    price = models.FloatField()

    class Meta:
        db_table = "price_observation"
        verbose_name = "Price Observation"
        verbose_name_plural = "Price Observations"
        constraints = [
            models.UniqueConstraint(
                fields=["district", "product", "date"],
                name="unique_price_observation"
            )
        ]

    def __str__(self):
        return f"{self.product} | {self.district} | {self.date} | {self.price}"
