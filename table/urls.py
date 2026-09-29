from django.urls import path

from . import views

urlpatterns = [
    path('play/<str:table_id>/<str:player_id>/', views.play_table, name='play_table'),
]
