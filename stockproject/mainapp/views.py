from concurrent import futures
from django.http.response import HttpResponse
from django.shortcuts import render
from yahoo_fin.stock_info import *

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


def stockTracker(request):
    """
    Module for tracking data of the selected stocks.
    """
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