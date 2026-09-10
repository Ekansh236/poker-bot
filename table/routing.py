from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/table/(?P<table_id>\w+)/(?P<player_id>\w+)/$', consumers.TableConsumer.as_asgi()),
]
