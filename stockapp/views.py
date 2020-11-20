from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone,dateformat

from stockapp.forms import *
from stockapp.models import *
import yfinance as yf
import json
from django.http import JsonResponse
from django.http import HttpResponse

from datetime import date
from django.views.decorators.csrf import ensure_csrf_cookie

import numpy as np
from sklearn.preprocessing import MinMaxScaler

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import LSTM
from tensorflow import keras


# loading_percentage = None

def home_stream(request):
    context = {}
    if request.method == 'GET':
        context['stockform'] = StockForm()
        return render(request, 'stockapp/home.html', context)
    
    stockform = StockForm(request.POST)
    context['stockform'] = stockform
    if not stockform.is_valid():
        return render(request, 'stockapp/home.html', context)

    ticker = request.POST.get("symbol")
    stock = None
    try:
        stock = Stock.objects.get(ticker=ticker)
        if stock.query_date == date.today():
            # print("stock from database try 1 :", stock)

            setBasicInfo(context, stock.info)
            setPriceInfo(context, stock.price)
            # setRecInfo(context, stock.recommend)
            return render(request, 'stockapp/home.html', context)
        else:
            addToDatabase(ticker)
            stock = None    
    except Stock.DoesNotExist:
        addToDatabase(ticker)
        

    # it was stored, so retrived
    if stock == None:
        try: 
            stock = Stock.objects.get(ticker=ticker)
            # print("stock from database try 2 :", stock)
        except Stock.DoesNotExist:
            context["error"] = "Invalid stock ticker"
            return render(request, 'stockapp/home.html', context)

    # print(len(Stock.objects.all()))
    
    setBasicInfo(context, stock.info)
    setPriceInfo(context, stock.price)
    # setRecInfo(context, stock.recommend)
    return render(request, 'stockapp/home.html', context)

def addToDatabase(ticker):
   
    stock = yf.Ticker(ticker)
   
    try :
        info = stock.info
        
        price_df = stock.history(period="5y")

        df_price_json = table(price_df)
    
        stock = Stock(ticker=info["symbol"], query_date=date.today(), info = info, price=df_price_json)
        stock.save()
    except :
        print("error api")
        pass
       
    
def setBasicInfo(context, info):
    if "longName" in info:
            context['name'] = info["longName"]
    if "city" in info:
        context['location'] = info["city"]
    if "state" in info:
        context['location'] += ", " + info["state"]  
    if "country" in info:
        context['location'] += ", " + info["country"]   
         
    if "logo_url" in info:
        context['icon'] = info["logo_url"]
    if "website" in info:    
        context['website'] =  info["website"]  
    if "symbol" in info:  
        context['symbol'] = info["symbol"]


    if "shortRatio" in info:
        context['short_ratio'] = info["shortRatio"]
    if "profitMargins" in info:
        context['profit_margin'] = info["profitMargins"]
    if "forwardPE" in info:
        context['f_pe'] = info["forwardPE"] 
    if "trailingPE" in info:
        context['t_pe'] = info["trailingPE"] 
    if "pegRatio" in info:
        context['peg'] = info["pegRatio"]     
    if "regularMarketPrice" in info:
        context['reg_price'] = info["regularMarketPrice"]         

def setPriceInfo(context, price):
    context['d'] = price
    print("conext d done")


def setRecInfo(context, recommend):
    context['recommend'] = recommend
    print(recommend)

def table(dataframe): 
    df = dataframe
    # print(df)
    # parsing the DataFrame in json format. 
    json_records = df.reset_index().to_json(orient ='records') 
    data = [] 
    data = json.loads(json_records) 
    # context = {'d': data} 
    # print(context)
    return data
     


# ---------------------------------------------------------------------------------------

# Ajax for deep learning

def display_pred(request, symbol):
    
    # if not request.user.id:
    #     return _my_json_error_response("You must be logged in to do this operation", status=403)
    if not symbol or request.method != 'GET':
        return my_json_error_response("You must use a GET request for this operation", status=404)

    # if not 'symbol' in request.GET or not request.GET['symbol'] or request.GET['symbol'].isspace():
    #     return my_json_error_response("You must enter a ticker symbol to predict.")

    # new_comment = Comment(text=request.POST['comment_text'], user_comment=request.user.user_profile.first(), 
    #             date=timezone.now(), post_of_comment =  Post.objects.get(id=request.POST['post_id']))
    # new_comment.save()
    
    data = deep_alg(request, symbol)  #it also calls loading_percentage http response

    # print("data is", data)
    return json_dumps_serializer_predict(request, data, symbol)


def json_dumps_serializer_predict(request, data, symbol):
    
  
    response_data_post = []
    
    
    print("req predicted data for symbol :", symbol)
    

    response_data = [{'price_pred' : data,'symbol' : symbol}]
    
    response_json = json.dumps(response_data)
    response = HttpResponse(response_json, content_type='application/json')
    response['Access-Control-Allow-Origin'] = '*'
    return response  

def my_json_error_response(message, status=200):
    # You can create your JSON by constructing the string representation yourself (or just use json.dumps)
    response_json = '{ "error": "' + message + '" }'
    return HttpResponse(response_json, content_type='application/json', status=status)


# def get_percentage(request): 
#     response_json = '{ "done_percentage": "' + loading_percentage + '" }' #not an array, but a response still
#     return HttpResponse(response_json, content_type='application/json')
# -----------------------------------------------------------------------------------------

# deep learning
def deep_alg(request, symbol):
    # global price_df
    # global loading_percentage
    

    price_df = yf.Ticker(symbol).history(period="5y")
    
    scaler=MinMaxScaler(feature_range=(0,1))
    df1=price_df.reset_index()['Close']
    df1=scaler.fit_transform(np.array(df1).reshape(-1,1))
    # print(df1[-10:])

    training_size=int(len(df1)*0.8)
    test_size=len(df1)-training_size
    train_data,test_data=df1[0:training_size,:],df1[training_size:len(df1),:1]
    
    # reshape into X=t,t+1,t+2,t+3 and Y=t+4
    time_step = 100 #BLOCKS of previous data of dataX
    X_train, y_train = create_dataset(train_data, time_step)
    X_test, ytest = create_dataset(test_data, time_step)

    print(X_test.shape), print(ytest.shape)

    X_train =X_train.reshape(X_train.shape[0],X_train.shape[1] , 1)
    X_test = X_test.reshape(X_test.shape[0],X_test.shape[1] , 1)

    model=Sequential()
    model.add(LSTM(50,return_sequences=True,input_shape=(100,1))) #3 layers
    model.add(LSTM(50,return_sequences=True)) #2 layers
    model.add(LSTM(50)) # 1 layer
    model.add(Dense(1)) #output
    model.compile(loss='mean_squared_error',optimizer='adam') 
    print(model.summary())

    model.fit(X_train,y_train,validation_data=(X_test,ytest),epochs=7,batch_size=64,callbacks=[])
    
    ### Lets Do the prediction and check performance metrics
    train_predict=model.predict(X_train)
    test_predict=model.predict(X_test)

    ##Transformback to original form
    train_predict=scaler.inverse_transform(train_predict)
    test_predict=scaler.inverse_transform(test_predict)

    x_input=test_data[len(test_data)-100:].reshape(1,-1)
    print(x_input.shape)

    temp_input=list(x_input)
    temp_input=temp_input[0].tolist() 

    nextdays = 60
    lst_output=[]
    n_steps=100
    i=0
    while(i<nextdays):
        if(len(temp_input)>100):
            #print(temp_input)
            x_input=np.array(temp_input[1:])
            x_input=x_input.reshape(1,-1)
            x_input = x_input.reshape((1, n_steps, 1))
            #print(x_input)
            yhat = model.predict(x_input, verbose=0)
            temp_input.extend(yhat[0].tolist())
            temp_input=temp_input[1:]
            #print(temp_input)
            lst_output.extend(yhat.tolist())
            i=i+1
        else:
            x_input = x_input.reshape((1, n_steps,1))
            yhat = model.predict(x_input, verbose=0)
            temp_input.extend(yhat[0].tolist())
            lst_output.extend(yhat.tolist())
            i=i+1
    

    # print(lst_output) 
    # PREDICTED VALUES

    day_old=np.arange(1,101)
    day_pred=np.arange(101,101+nextdays) 
    pred_values = scaler.inverse_transform(lst_output)
    old_values = scaler.inverse_transform(df1[len(df1)-100:]) #last 100 days
    

    # all_values = df1.tolist()
    # all_values.extend(lst_output)
    # all_values = scaler.inverse_transform(all_values).tolist()
    
    
    # print(lst_output[-3:])
    # print(len(all_values))
    
    context = {'day_old': day_old.tolist(), 'day_pred': day_pred.tolist(), 'old_values': convertToList(old_values.tolist()), 'pred_values': convertToList(pred_values.tolist())} 
    
    return context


# helper deep_alg

# convert an array of values into a dataset matrix
# Making independent (dataY) and dependent (dataX) features for BOTH test and training data.
def create_dataset(dataset, time_step=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-time_step-1):
        a = dataset[i:(i+time_step), 0]   ###i=0, 0,1,2,3-----99 (dataX)  100th (dataY)
        dataX.append(a)
        dataY.append(dataset[i + time_step, 0])
    return np.array(dataX), np.array(dataY)

# convert tolist arrays of single arrays to list
def convertToList(arr):
    res = []
    for a in arr:
        res.append(a[0])
    return res    

# class CustomCallback(keras.callbacks.Callback):
#     def __init__(self, request):
#         """ Save params in constructor
#         """
#         self.req = request

#     def on_epoch_end(self, epoch, logs=None):
#         keys = list(logs.keys())
#         print("Done {} %".format(epoch+1))
#         # loading_percentage = (str(20*(epoch+1))+'%')
#         # self.req.session['loading_percentage'] = loading_percentage
        