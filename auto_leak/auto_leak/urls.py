from django.urls import path, include
from leakapp import views


urlpatterns = [
    path('', views.user_login, name='login'),
]