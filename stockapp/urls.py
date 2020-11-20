from django.urls import path
from stockapp import views

urlpatterns = [
    path('', views.home_stream, name='home'),
    path('home', views.home_stream, name='home'),
    path('display/<str:symbol>', views.display_pred),
]

