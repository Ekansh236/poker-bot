from django.urls import path

from . import views

urlpatterns = [
    path('', views.lobby, name='lobby'),
    path('create/', views.create_game, name='create_game'),
    path('join/', views.join_game, name='join_game'),
    path('join/<str:table_id>/', views.join_game, name='join_game_prefilled'),
    path('play/<str:table_id>/<str:player_id>/', views.play_table, name='play_table'),
]
