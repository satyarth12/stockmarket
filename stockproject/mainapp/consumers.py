import json
from .models import StockDetail
from .views import stockPicker
from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from urllib.parse import parse_qs

from django_celery_beat.models import PeriodicTask, IntervalSchedule
import copy
import html5lib

class StockConsumer(AsyncWebsocketConsumer):

    #creating a sync function 
    @sync_to_async
    def add_celery_beat(self, stockpicker):
        task = PeriodicTask.objects.filter(name="every-10-seconds")

        # this if statement is to check if the stock is already present in the celery task list or not
        # to reduce the unrequired API calls
        if len(task) > 0:
            task = task.first()
            args = json.loads(task.args)
            args = args[0]

            for x in stockpicker:
                if x not in args:
                    args.append(x)

            task.args = json.dumps([args])
            task.save()

        else:
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=10, period=IntervalSchedule.SECONDS
            )
            task = PeriodicTask.objects.create(
                interval=schedule,
                name="every-10-seconds",
                task="mainapp.tasks.update_stock",
                args=json.dumps([stockpicker])
            )
    

    #another sync function but for django ORM
    @sync_to_async
    def add_stock_detail(self, stockpicker):
        user  = self.scope["user"]
        for i in stockpicker:
            obj, created = StockDetail.objects.get_or_create(stock=i)
            obj.user.add(user)


    @sync_to_async
    def select_user_stocks(self):
        user = self.scope["user"]
        user_stocks = user.stockdetail_set.values_list('stock', flat=True)
        return list(user_stocks)
    

    @sync_to_async
    def helper_func(self):
        """
        This module if for removing the args from the task if it already exists
        and also to remove the whole task if the any of the user of those args are disconnected
        """
        user = self.scope["user"]
        stocks = StockDetail.objects.filter(user = user)
        task = PeriodicTask.objects.get(name = "every-10-seconds")
        args = json.loads(task.args)
        args = args[0]

        for i in stocks:
            i.user.remove(user)
            if i.user.count() == 0:
                args.remove(i.stock)
                i.delete()
        
        if args == None:
            args = []
        
        if len(args) == 0:
            task.delete()
        else:
            task.args = json.dumps([args])
            task.save()


    """
    Async Functions
    """
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "stock_%s" % self.room_name
        print(self.room_group_name)

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Parse querystring
        query_params = parse_qs(self.scope["query_string"].decode())
        print(query_params)

        stockpicker = query_params["stockpicker"]

        # add to celery beat
        await self.add_celery_beat(stockpicker)

        #add user to stockdetail
        await self.add_stock_detail(stockpicker)

        await self.accept()



    async def disconnect(self, close_code):
        await self.helper_func()

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                # type is the function that will actually send the data to channels
                "type": "stock_update",
                "message": message,
            },
        )

    # Receive message from room group
    async def send_stock_update(self, event):
        message = event["message"]

        """
        Creating a copy for the message because if we change the event["message"], then the change will
        occur for every user because we'll be changing the whole event itself.

        Also, python is a pass object by reference thing. 
        """
        new_message = copy.copy(message)

        user_stocks = await self.select_user_stocks()
        keys = new_message.keys()

        #sending user specific data only
        for key in list(keys):
            if key in user_stocks:
                pass
            else:
                del new_message[key]

        # Send message to WebSocket
        await self.send(text_data=json.dumps(new_message))
