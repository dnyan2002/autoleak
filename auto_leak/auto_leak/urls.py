from django.urls import path, include
from leakapp import views


urlpatterns = [
    path('', views.user_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('leakapp/', views.LeakAppMasterDataView.as_view(), name='leakapp_list'),
    path('leakapp/edit/<int:pk>/', views.LeakAppMasterDataView.as_view(), name='leakapp_edit'),
    path('leakapp/delete/<int:pk>/', views.LeakAppMasterDataView.as_view(), name='leakapp_delete'),
    path('leakapp/search/', views.search_part_numbers, name='leakapp_search'),
]