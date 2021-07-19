from concurrent import futures
from django.http.response import HttpResponse
from django.shortcuts import render
from yahoo_fin.stock_info import *
from asgiref.sync import async_to_sync, sync_to_async

import html5lib

import time
import concurrent.futures

def stockPicker(request):
    stock_picker = tickers_nifty50()
    context = {
        'stockpicker':stock_picker
    }
    return render(request, 'mainapp/stockpicker.html', context)




def get_quote(x):
    data = {}
    data[x] = get_quote_table(x)
    return data

@sync_to_async
def isAuth(request):
    if not request.user.is_authenticated:
        return False
    return True

async def stockTracker(request):
    """
    Module for tracking data of the selected stocks.
    """
    #for checking the auth of the current user
    is_logined = await isAuth(request)
    if not is_logined:
        return HttpResponse('Login to continue')

    stocks = request.GET.getlist('stockpicker')
    available_stocks = tickers_nifty50()
    data = {}

    for i in stocks:
        if i in available_stocks:
            pass
        else:
            return HttpResponse("Error")

    start = time.time()

    #using threadpool for concurrent srapping of data
    with concurrent.futures.ThreadPoolExecutor(len(stocks)) as executor:
        result = executor.map(get_quote, [i for i in stocks])

    end = time.time()
    print(end-start)

    for li in list(result):
        data.update(li)
    print(data)
    return render(request, 'mainapp/stocktracker.html', {'data': data, 'room_name':'track'} )