from django.urls import path, include, re_path
from leakapp import views
from django.views.static import serve
from django.conf import settings
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.user_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('leakapp/', views.LeakAppMasterDataView.as_view(), name='leakapp_list'),
    path('leakapp/edit/<int:pk>/', views.LeakAppMasterDataView.as_view(), name='leakapp_edit'),
    path('leakapp/delete/<int:pk>/', views.LeakAppMasterDataView.as_view(), name='leakapp_delete'),
    path('leakapp/search/', views.search_part_numbers, name='leakapp_search'),
    path("leak-test/", views.get_leak_test_data, name="leak_test"),
    path("search-part-numbers/", views.search_part_numbers_for_leak_test, name="search_part_numbers"),
    path('get-latest-filter-values/', views.get_latest_filter_values, name='get_latest_filter_values'),
    path('get-highest-filter-value/', views.get_highest_filter_value, name='get_highest_filter_value'),
    path('report', views.report_screen, name='report'),
    path('get-latest-leak-data/', views.get_latest_leak_data, name='get_latest_leak_data'),
    re_path(r'^media/(?P<path>.*)$',serve,{'document_root' : settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$',serve,{'document_root' : settings.STATIC_ROOT}),
]
