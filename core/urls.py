from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from app import views # Barcha funksiyalarni bitta views orqali chaqiramiz

urlpatterns = [
    # 1. MAXSUS ADMIN FUNKSIYALARI (Bular har doim tepada bo'lishi shart!)
    # Statistika va Excelga eksport qilish
    path('admin/statistics/', views.admin_statistics, name='admin_statistics'),
    path('admin/statistics/export/', views.export_results_excel, name='export_results_excel'),
    
    # Savollarni ommaviy yuklash (Bulk Upload)
    path('admin/bulk-upload/<int:test_id>/', views.bulk_upload_view, name='bulk_upload'),

    # 2. STANDART ADMIN PANEL (Buni pastga tushirdik)
    path('admin/', admin.site.urls),

    # 3. FOYDALANUVCHI (STUDENT) QISMI
    # /dashboard/ manzili va asosiy sahifa
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('', views.dashboard, name='home'), 
    
    # Test topshirish sahifasi
    path('test/<int:test_id>/', views.take_test, name='take_test'),

    # 4. AVTORIZATSIYA (KIRISH VA CHIQISH)
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('result/<int:result_id>/', views.result_detail, name='result_detail'),
]