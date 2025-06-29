from channels.generic.websocket import AsyncWebsocketConsumer
import json

class OptimizationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Bağlantı kurulduğunda optimization_updates grubuna katıl
        await self.channel_layer.group_add(
            'optimization_updates',
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Bağlantı kesildiğinde gruptan ayrıl
        await self.channel_layer.group_discard(
            'optimization_updates',
            self.channel_name
        )

    async def optimization_update(self, event):
        # Optimizasyon sonuçlarını client'a gönder
        await self.send(text_data=json.dumps({
            'monte_carlo': event['monte_carlo'],
            'taguchi': event['taguchi'],
            'genetic': event['genetic']
        })) 