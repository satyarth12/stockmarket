import asyncio
from celery import shared_task
from yahoo_fin.stock_info import *

import time
import concurrent.futures
import html5lib

from channels.layers import get_channel_layer
import asyncio

import simplejson as json


def get_quote(x):
    data = {}
    data[x] = json.loads(json.dumps(get_quote_table(x), ignore_nan=True))
    return data


@shared_task(bind=True)
def update_stock(self, stockpicker):
    """
    This method is for retreiving the stock data, using celery, that has been selected by all the user.

    The approach is that:
    Stocks will be getting into the queue for of celery only if that stock data is not present in the task queue.
    This way we will decrease the server API calls.
    """
    data = {}
    available_stocks = tickers_nifty50()

    for i in stockpicker:
        if i in available_stocks:
            pass
        else:
            # removing stocks from the stockpicker list
            stockpicker.remove(i)

    # using threadpool for concurrent scrapping of data
    with concurrent.futures.ThreadPoolExecutor(len(stockpicker)) as executor:
        result = executor.map(get_quote, [i for i in stockpicker])

    for li in list(result):
        data.update(li)

    # send data to the websocket group
    channel_layer = get_channel_layer()
    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        channel_layer.group_send(
            "stock_track",
            {
                "type": "send_stock_update",
                "message": data,
            }
        )
    )

    return "Done"
