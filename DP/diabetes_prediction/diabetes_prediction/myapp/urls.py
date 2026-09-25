from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home_alt'),
    path('get-started/', views.get_started, name='get_started'),
    path('check-email/', views.check_email, name='check_email'),
    path('login/', views.user_login, name='user_login'),
    path('registration/', views.user_registration, name='user_registration'),
    path('health-record/', views.health_record, name='health_record'),
    path('view-profile/', views.view_profile, name='view_profile'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('predict-risk/', views.predict_risk, name='predict_risk'),
    path('predict/', views.add_prediction, name='predict'),
    path('add-prediction/', views.add_prediction, name='add_prediction'),
    path('view-prediction/', views.view_prediction_page, name='view_prediction'),
    path('prediction-history/', views.prediction_history, name='prediction_history'),
    path('database-tracking/', views.prediction_history, name='database_tracking'),
    path('analytics-dashboard/', views.analytics_dashboard, name='analytics_dashboard'),
    path('recommendation-engine/', views.recommendation_engine, name='recommendation_engine'),
    path('recommendations/', views.recommendation_engine, name='recommendations'),
    path('logout/', views.user_logout, name='user_logout'),
]





