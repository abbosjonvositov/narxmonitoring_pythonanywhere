from django.urls import path
from .views import *

# Сдесь будим писать пути для вьюшек
urlpatterns = [
    path('', LandingPageView.as_view(), name='landing_page'),
    path("profile_page/", ProfilePageView.as_view(), name="profile_page"),
    path('upload/<str:code>/', upload_view, name='upload_files'),
    path('update/<str:code>/', update_view, name='update_db'),  # NEW
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', LoginView.as_view(), name='login'),
    path("api/latest-price-by-product/", LatestPriceByProductAPIView.as_view(), name="latest-price-by-product"),
    path("api/dashboard", DashboardAPIView.as_view(), name="dashboard"),
    path("api/products/performance/", ProductPerformanceView.as_view(), name="product-performance"),
]
