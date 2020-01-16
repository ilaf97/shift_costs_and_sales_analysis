#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import datetime as dt
from collections import defaultdict

def break_time_processing(break_time, shift_data, start, end):
    
    for row in shift_data.break_notes:
        
        #check for spaces in  substring
        if ' ' in break_time:
            break_time = break_time.replace(' ', '')
        
        #Check to see if contains 'PM'
        if 'PM' in break_time:
            bt = break_time.replace('PM', '')

            #Replace '.' in time with ':' for datetime format parsing
            if '.' in bt:
                bt = bt.replace('.', ':')
            
            #Add ':00' substr to end to convert into suitable format for datetime parsing
            else:
                bt = bt + ':00'
                
            bt = dt.datetime.strptime(bt, '%H:%M') + dt.timedelta(hours = 12) 
            #Convert to dateteime format and add 12 hours to make correct 24hr clock time
            
        #Check to see if contains 'AM'
        if 'AM' in break_time:
            bt = break_time.replace('AM', '')
            
            #Replace '.' in time with ':' for datetime format parsing
            if '.' in bt:
                bt = bt.replace('.', ':')
            
            #Add ':00' substr to end to convert into suitable format for datetime parsing
            else:
                bt = bt + ':00'
                
            bt = dt.datetime.strptime(bt, '%H:%M') #Convert to dateteime format
        
        #Case when no AM or PM labels
        if 'AM' and 'PM' not in break_time:
            
            #Replace '.' in time with ':' for datetime format parsing
            if '.' in break_time:
                bt = break_time.replace('.', ':')
            
            #Add ':00' substr to end to convert into suitable format for datetime parsing
            else:
                bt = break_time + ':00'   
                                
            bt = dt.datetime.strptime(bt, '%H:%M')  #Convert to datetime format
            
        #Check to see if breaktime falls between shift start and end times
        if start <= bt.time() <=end:
            bt = bt.time()
        
        #Add 12 hours as it must be inside shift times
        else:
            bt = bt + dt.timedelta(hours = 12)
            bt = bt.time()

    return bt


def process_shifts(path_to_csv):    

    shift_data = pd.read_csv(path_to_csv)
    
    #1. DEFINE SEPARATE LISTS CONTAINING ALL SHIFT AND BREAK INFORMATION                     
    #Define empty arrays to hold shift start and end time data     
    start = []
    end = []
    cost = []
    
    #Create list of shift start times
    for row in shift_data.start_time:
        s = dt.datetime.strptime(row, '%H:%M') #Covert times to datetime type
        start.append((s.time()))               #Append time to array

    #Create list of shift end times
    for row in shift_data.end_time:
        e = dt.datetime.strptime(row, '%H:%M') #Covert times to datetime type
        end.append((e.time()))                 #Append time to array
    
    #Create list of shift cost 
    for row in shift_data.pay_rate:
        cost.append(row)

    #Define empty break arrays
    b_start = [None]*len(start)
    b_end = [None]*len(start)
    j = 0
    
    #Iterate through rows in break_notes column
    for row in shift_data.break_notes:
        break_start = row.split("-", 1)[0]  #Take 1st time entry
        break_end = row.split("-", 1)[1]    #Take 2nd time entry
        
        #Pass arguments to break processing fucntion to create lists of break start/end times       
        b_start[j] = break_time_processing(break_start, shift_data, start[j], end[j])
        b_end[j] = break_time_processing(break_end, shift_data, start[j], end[j])
        j = j + 1
      

    #2. FIND EMPLOYEE WORKING TIMES AND CALCULATE RESULTING LABOUR COSTS                     
    #Define empty lists/dictionaries
    h = []  
    hour_cost = []
    labour_cost = {}
    
    #Loop counters
    i = 0   
    j = 0   
    midnight = dt.datetime.strptime('00:00', '%H:%M')   #Find midnight 
   
    #Define new arry where column represents each hour in day and row each worker
    working = [[0 for x in range(24)] for y in range(len(start))]   

    #Create array of 24 hours (of type datetime)
    for i in range (0,24):
        h.append((midnight + dt.timedelta(hours = i)).time())
        #timedelta function adds i hours to midnight time
        
    #Iterate over all employees/rows
    while j < len(start): #j represents row number in orignal CSV file
        
        #Iterate over all hours in day
        for i in range(0, 24):
            
            #Find hours that employee works between shift start and end times
            if start[j] <= h[i] < end[j]:
                working[j][i] = cost[j]    #i represents columns/hours, and j rows/employees
                
            #If not working, give entry of zero (no cosr)
            else:
                working[j][i] = 0
            
            #Set to zero (not working) if given hour (h[i]) falls in range of break
            if b_start[j] <= h[i] < b_end[j]:
                working[j][i] = 0
                
            hour_cost = np.sum(working, axis=0) #Calculate the hourly cost by summing all columns
           
            if hour_cost[i] != 0:   #Remove entries where hourly cost = 0 (nobody working)
                labour_cost[str(h[i].strftime('%H')+':00')] = hour_cost[i] 
                #Create dictionary of labour costs for each hour where someone working
    
        j = j + 1   #Increase loop counter         
  
    return labour_cost


def process_sales(path_to_csv):
    
    transactions = pd.read_csv(path_to_csv)
  
    #Define empty lists/dictionary
    sale_time = []
    revenue = []
    sales = {}
    j = 0   #Loop counter
    
    #Create list of sales times
    for row in transactions.time:
        timestamp = dt.datetime.strptime(row, '%H:%M')
        sale_time.append(timestamp)

    #Create list of revenues
    for row in transactions.amount:
        revenue.append(row)
    
    #Create dictionary of all transactions      
    for j in range (0, len(revenue)):
        sales[(sale_time[j].time())] = revenue[j]
        
    d = defaultdict(int)     #Define default dictionary
    
    #Add all revenues which occur during same hour    
    for t, val in sales.items():
        d[t.strftime('%H')+':00'] += val
        
    #Pass all dictionary items to list that map across onto another list to a complete dictionary  
    d2 = dict(map(list, d.items()))
    
    #Round hourly sales revnue to 2d.p.
    for t, val in d2.items():
        d2[t] = float(round(val, 2))
      
    #Pass all dictionary items to list that map across onto another list to a complete dictionary  
    hour_totals = dict(map(list, d2.items()))
        
    return hour_totals


def compute_percentage(shifts, sales):

    #This solution assumes that sales only occur when someone is working
    
    d = defaultdict(int) #Define default dictionary
        
    for t, val in shifts.items():   #Iterate over all dictionary entires  
        if t not in sales:      #Case when time t not in sales dictionary
            d[t] = -shifts[t]   #Set sales "revenue" to labour cost of hour
        
        #Find percentage of labour cost per sales
        else:
            d[t] = round(float((shifts[t]/sales[t])*100), 2)
            #round ensures that calculated value remains to 2d.p. only
        
    percentages = dict(map(list, d.items())) #Map results to new dictionary
    
    return percentages


def best_and_worst_hour(percentages):
                
    best_worst_dict = {k: v for k, v in sorted(percentages.items(), key=lambda item: item[1], reverse=True)}
    #Sort percentages dict in reverse order and add entires to new dictionary
        
    best_worst = [] #Define empty list
    
    for k, val in best_worst_dict.items():
        best_worst.append(k)
            
    best_worst = [best_worst[0], best_worst[-1]] 
    #Keep only best and worst hours (first and last array elements)
        
    return best_worst


def main(path_to_shifts, path_to_sales):

    shifts_processed = process_shifts(path_to_shifts)
    sales_processed = process_sales(path_to_sales)
    percentages = compute_percentage(shifts_processed, sales_processed)
    best_hour, worst_hour = best_and_worst_hour(percentages)
    return best_hour, worst_hour, percentages

#Print output to console
path_to_sales = "/Users/isaacfrewin/Documents/Tenzo Task/transactions.csv"
path_to_shifts = "/Users/isaacfrewin/Documents/Tenzo Task/work_shifts.csv"
best_hour, worst_hour, percentages = main(path_to_shifts, path_to_sales)
print('Best hour:', best_hour, '\nWorst hour:', worst_hour, '\n\nLabour cost as % of sales:')
for k, v in percentages.items():
   print(k, ':', v)

print('(Negative entry when no sales - illustrates total labour cost in £ for this hour)')


