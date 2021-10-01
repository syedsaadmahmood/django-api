from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter

import django_synergy.notifications.routing
import django_synergy.notifications.consumers


application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter(
            django_synergy.notifications.routing.websocket_urlpatterns
        )
    ),
    "channel": ChannelNameRouter({
        "notification-send": django_synergy.notifications.consumers.UserNotificationAsyncConsumer,
    }),
})
