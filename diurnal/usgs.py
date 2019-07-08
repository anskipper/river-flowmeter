import pandas as pd
from diurnal import fileIO as fio
import datetime as dt

def readUSGS(filename,headerNum):
    df = pd.read_csv(filename, sep='	',header=headerNum,index_col=2)
    df = df.drop(['agency_cd','site_no','tz_cd'],axis=1)
    df = df.drop(['20d'])
    df.index = pd.to_datetime(df.index)
    #rename the parameter columns to better names e.g., y-gage-ft, Q-cfs, rain-in
    # depth always reported as GAGE DEPTH
    parameterNames = ['river elevation', 'resevoir elevation', 'Q-river', 'rain-in']
    parameterList = ['00065','00062','00060','00045']
    for j in range(0,len(df.columns),2):
        #paramterCode format #####_000##
        parameterCode = df.columns[j].split('_',1)[1]
        parameterName = parameterNames[parameterList.index(parameterCode)]
        df = df.rename(columns={df.columns[j] : parameterName, df.columns[j+1] : parameterName + '-Quality'})
        #also make the y, Q, res-el,and/or rain values numeric
        df[df.columns[j]]=df[df.columns[j]].astype('float64')
    return(df)

def readFMtoUSGS(fileList,usgsDir):
    fm2usgs = fio.findFileInList(fileList=fileList,key='FMtoUSGS')
    df = pd.read_csv(usgsDir + '\\' + fm2usgs,index_col=0)
    return(df)

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

def constructMeanFlow(tStart,tEnd,dfMeans):
    daysDiff = getTimeDiff(tStart,tEnd,'days')
    wVals = [(tStart + dt.timedelta(days=x)).weekday() for x in range(0,daysDiff+1)]    
    meanFlow = []
    dateTimes = []
    day = dt.datetime(tStart.year,tStart.month,tStart.day)
    for k in range(0,len(wVals)):
        if wVals[k] > 4: #WEEKEND
            col = 'Weekend'
        else:
            col = 'Weekday'
        if k==0: # pre-comp period
            meanFlow.extend(dfMeans.loc[tStart.time():,col])
            h = getTimeDiff(tStart.date() + dt.timedelta(days=1),tStart,returnState='hours')
            m = getTimeDiff(tStart.date() + dt.timedelta(days=1),tStart,returnState='minutes')
            dateTimes.extend([tStart + dt.timedelta(minutes=x) for x in range(0,h*60 + m,15)])
        elif k==len(wVals)-1: # end of r2
            meanFlow.extend(dfMeans.loc[:tEnd.time(),col])
            h = getTimeDiff(tEnd,tEnd.date(),returnState='hours')
            m = getTimeDiff(tEnd,tEnd.date(),returnState='minutes')
            dateTimes.extend([dt.datetime(tEnd.year,tEnd.month,tEnd.day) 
                        + dt.timedelta(minutes=x) for x in range(0,h*60 + m + 15,15)])
        else:
            meanFlow.extend(dfMeans.loc[:,col])
            day += dt.timedelta(days=1)
            dateTimes.extend([day + dt.timedelta(minutes=x) for x in range(0,24*60,15)])
        # construct the dataframe for plotting
    df = pd.Series(data=meanFlow,index=dateTimes,name='Mean Flow')
    return (df)

