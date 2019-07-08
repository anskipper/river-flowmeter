import numpy as np
import pandas as pd
import datetime as dt

# plotting
colorWkd = 'xkcd:leaf green'
colorWke = 'xkcd:hunter green'
colorMean = 'xkcd:light purple'
colorRain = 'xkcd:dark sky blue'
gridColor = 'xkcd:grey'


def identifyStorms(dfDaily, dfHourly,gageName):
    dailyThresh = 0.1 #in
    peakThresh = 0.03 #in
    intenseThresh = 0.8 #percent
    rainDates = []

    # if the daily rain total exceeds the daily threshold, add the rain date to the list
    mask = dfDaily[gageName] > dailyThresh 
    rainDates.extend(dfDaily.index[mask])

    # PEAK THRESH
    mask = dfDaily[gageName] >= peakThresh
    possPeakDates = dfDaily.index[mask]
    
    for date in possPeakDates:
        # only check if we havent already added it to the rain dates from the daily threshold
        if date not in rainDates:
            #check to see if the peak is greater than the peakThresh
            peak = dfHourly.loc[date:date+dt.timedelta(hours=23),gageName].values.max()
            # if the hourly peak is greater than the peak threshold, add the rain date to the list
            if peak >= peakThresh:
                rainDates.extend([date])
            else:
                pass
        else:
            pass
    
    #INTENSITY THRESH
    mask =  dfDaily[gageName] > 0
    possIntenseDates = dfDaily.index[mask]

    for date in possIntenseDates:
        if date not in rainDates:
            drt = dfDaily.loc[date,gageName]
            peak = dfHourly.loc[date:date+dt.timedelta(hours=23),gageName].values.max()
            if peak/drt/1.0 > intenseThresh:
                rainDates.extend([date])
            else:
                pass
        else:
            pass

    rainDates.sort()
    return(rainDates)

def getTimeDiff(date1,date2,returnState):
    date1 = pd.to_datetime(date1)
    date2 = pd.to_datetime(date2)
    if date2 >= date1:
        dateDiff = date2 - date1
    else:
        dateDiff = date1 - date2
    # convert to days and seconds
    days, seconds = dateDiff.days, dateDiff.seconds
    # covert to total hours and total minutes
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    returnOptions = {'days': days, 'hours': hours, 'minutes' : minutes, 'seconds' : seconds}
    return(returnOptions[returnState])

def stormAnalyzer(dfHourly,date,gageName):
    # find the first value that is on this date and the hourly rain total exceeds 0
    mask = (dfHourly.index>=date) & (dfHourly.index<date+dt.timedelta(days=1)) & (dfHourly.loc[:,gageName]>0)
    if dfHourly.index[mask].empty:
        tStart = date
        eventDur = 71
        eventRT = 0
        stormDur = 24
        stormRT = 0
    else:
        tStart = dfHourly.index[mask][0]
        # find the time that it stops raining within a 71 hour period
        # this is the EVENT DURATION
        mask = (dfHourly.index>=tStart) & (dfHourly.index<tStart+dt.timedelta(days=2,hours=23)) & (dfHourly.loc[:,gageName]>0)
        dur = getTimeDiff(date1=dfHourly.index[mask][-1],date2=tStart,returnState='hours')
        # the duration has to be at least 1 hour to count
        if dur > 0:
            eventDur = dur
            #find the rain total within the event duration
            eventRT = dfHourly.loc[tStart:tStart+dt.timedelta(hours=eventDur),gageName].sum()
            # set the storm duration as the minimum of the event duration and 24 hours
            stormDur = min(eventDur,24.0)
            #find the rain totals within storm duration
            stormRT = dfHourly.loc[tStart:tStart+dt.timedelta(hours=stormDur),gageName].sum()
        else:
            pass
    return(tStart,eventDur,eventRT,stormDur,stormRT)

def getStormData(dfDaily,dfHourly,gageName):
    # define start and end ranges
    startDate = dfDaily.index[0]
    endDate = dfDaily.index[-1]

    # find that dates that meet the storm criteria
    rainDates = identifyStorms(dfDaily=dfDaily,dfHourly=dfHourly,gageName=gageName)
    # check to see if any of the storm analysis period will be outside the date range; if so, delete that date from the list
    if rainDates[0] - dt.timedelta(days=1)<startDate:
        del rainDates[0]
    elif rainDates[-1] + dt.timedelta(days=2)>endDate:
        del rainDates[-1]
    else:
        pass
    
    # find the time that the rain starts for each date
    tStart = []
    eventDur = []
    eventRT = []
    stormDur = []
    stormRT = []
    for date in rainDates:
        # find the first value that is on this date and the hourly rain total exceeds 0
        mask = (dfHourly.index>=date) & (dfHourly.index<date+dt.timedelta(days=1)) & (dfHourly.loc[:,gageName]>0)
        tStart.extend([dfHourly.index[mask][0]])
        # find the time that it stops raining within a 71 hour period
        # this is the EVENT DURATION
        mask = (dfHourly.index>=tStart[-1]) & (dfHourly.index<tStart[-1]+dt.timedelta(days=2,hours=23)) & (dfHourly.loc[:,gageName]>0)
        dur = getTimeDiff(date1=dfHourly.index[mask][-1],date2=tStart[-1],returnState='hours')
        # the duration has to be at least 1 hour to count
        if dur > 0:
            eventDur.extend([dur])
            #find the rain total within the event duration
            eventRT.extend([dfHourly.loc[tStart[-1]:tStart[-1]+dt.timedelta(hours=eventDur[-1]),gageName].sum()])
            # set the storm duration as the minimum of the event duration and 24 hours
            stormDur.extend([min(eventDur[-1],24.0)])
            #find the rain totals within storm duration
            stormRT.extend([dfHourly.loc[tStart[-1]:tStart[-1]+dt.timedelta(hours=stormDur[-1]),gageName].sum()])
        else:
            #delete the tStart bc theres not actually an event
            del tStart[-1]
    
    df = pd.DataFrame(data={'Storm Dur': stormDur, 'Storm Rain': stormRT, 'Event Dur': eventDur, 'Event Rain': eventRT},index=tStart)
    return(df)

def readTotalFlow(filename):
    df= pd.read_csv(filename,index_col=0)
    df.index = pd.to_datetime(df.index)
    df.index = df.index.time
    return(df)

# tStart is a datetime object (e.g., 01/01/2018 13:00:00) and stormDur is an integer of hours (e.g., 6) that will be within a range [0,24]
def constructMeanFlow(tStart,stormDur,dfMeans):
    # pre-compensation
    pc = tStart - dt.timedelta(days=1)
    # end of storm
    stormEnd = tStart + dt.timedelta(hours=stormDur)
    # recovery 1
    r1 = stormEnd + dt.timedelta(days=1) 
    # recovery 2
    r2 = r1 + dt.timedelta(days=1)
    # if the storm goes into the nexxt day
    if (stormEnd.date() - tStart.date()).days >0:
        # weekday values
        wVals = [pc.weekday(),tStart.weekday(),stormEnd.weekday(),r1.weekday(),r2.weekday()]
    else:
        wVals = [pc.weekday(),tStart.weekday(),r1.weekday(),r2.weekday()]
    
    colorWkd = 'xkcd:leaf green'
    colorWke = 'xkcd:hunter green'
    meanFlow = []
    color = []
    for k in range(0,len(wVals)):
        if wVals[k] > 4: #WEEKEND
            col = 'Weekend'
            colorVal = colorWke
        else:
            col = 'Weekday'
            colorVal = colorWkd
        color.extend([colorVal])
        if k==0: # pre-comp period
            meanFlow.extend(dfMeans.loc[pc.time():,col])
        elif k==len(wVals)-1: # end of r2
            meanFlow.extend(dfMeans.loc[:r2.time(),col])
        else:
            meanFlow.extend(dfMeans.loc[:,col])
    # construct the dataframe for plotting
    hours = getTimeDiff(date1=pc,date2=r2,returnState='hours')
    dateTimes = pd.date_range(pc,periods=hours*60/15 + 1, freq = '15min')
    df = pd.Series(data=meanFlow,index=dateTimes,name='Mean Flow')
    df.index = pd.to_datetime(df.index)
    return (df,color)