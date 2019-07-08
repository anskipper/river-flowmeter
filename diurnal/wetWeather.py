''' 
This code analyzes a flowmeter for a particular date range to identify the I&I (inflow and infiltration) volume in million gallons (MG) of storms that occur within the analysis period.

What qualifies as a storm? 
1) a daily rain total (DRT) > 0.1 in
2) a daily rain peak (DRP) > 0.03 in
3) DRP/DRT >= 80%

The first metric determines whether it has rained a lot and the second and third determines whether it has rained intensely. 

There are four phases of the storm analysis: 
1) Precomposition
    Precomposition (PC) occurs 24 hours before the start time of the storm (resolution of hours).
    In this phase, the mean difference between the instantaneous, measured flowrate (Qi) and the dry weather mean (Qm) is determined. During the calculation of the I&I volume, Qm will be shifted uniformly by this amount.
2) Storm
    Every date that means the storm criteria listed above is quantified as a storm. 
    First the time that it starts raining (tStart) will be found. PC will be [tStart-24 hrs, tStart).
    Next the time that it stops raining (tStop) will be found. This will be the event duration (eventDur). The eventDur will be taken as the minimum of (tStop, 71 hrs). The rain total in this duration will be reported as eventRainTotal.
    Lastly the storm duration (stormDur) will be found. It is defined as the minimum of (eventDur,24 hrs). The rain total in this duration will be reported as stormRainTotal.
3) Recovery 1
    Occurs (tStart+stormDur, tStart+stormDur+24hrs]
4) Recovery 2
    Occurs (R1end, R1end+24 hrs]

The files to read in for the storm analysis are:
1) a gage file which connects the flow meter to its gage (subject to change), eg 'FMtoRG.txt'
2) daily rain totals, eg 'RG_daily_20180101-20190331.txt'
3) hourly rain totals, eg 'RG_hourly_20180101-20190331.txt'

Next the I&I volume is found for each storm. 
1) First find the mean curves for the dates in [PC,S,R1,R2]. These are found in a file this has been produced by the dryWeather.py analysis called [flowmeter name]_meanFlows.csv.
2) Shift the mean (Qm) by that storm's PC value.
3) Find the areas under the difference between Qi and Qm
    if the areas < 0: pass 
        It's unlikely that our pipes are working perfectly, so likely this indicates a malfunction of the rain gage sensor.
    else: report the gross I&I volume

Later, we will add an analysis portion to find the net I&I into a particular flow monitor by subtracting the gross I&I volumes for upstream flow monitors. Currently, the schematic is being verified and updated.
'''

#imports
import pandas as pd
from diurnal import dryWeather as dw
from diurnal import findRainEvents as fRE
import datetime as dt
import numpy as np
import math
'''
# set directories, files, etc
flowDir = 'P:\\PW-WATER SERVICES\\TECHNICAL SERVICES\\Anna'
gageFile = flowDir + '\\FMtoRG.txt'
dailyFile = flowDir + '\\RG_daily_20180101-20190331.txt'
hourlyFile = flowDir + '\\RG_hourly_20180101-20190331.txt'

# before batch
fmname = 'BC01A'
t = 'BC01A_28660533.txt'
flowFile = flowDir + '\\' + t
meanFile = flowDir + '\\2018\\Big Creek'+ '\\' + fmname + '\\' + fmname + '_meanFlows.csv'
'''

def readTotalFlow(filename):
    df= pd.read_csv(filename,index_col=0)
    df.index = pd.to_datetime(df.index)
    df.index = df.index.time
    return(df)

def abstrapz(y,x=None,dx=1.0):
    y = np.asanyarray(y)
    if x is None:
        d = dx
    else:
        x = np.asanyarray(x)
        d = np.diff(x)
    ret = (d * (y[1:] + y[:-1])/2.0)
    return(ret[ret>0].sum())

def stormGrossQ(stormDate,fmname,gageName,dfHourly,flowFile,meanFile,diameterFile,format):
    # find the info about the storm
    tStart,eventDur,eventRT,stormDur,stormRT = fRE.stormAnalyzer(dfHourly=dfHourly,date=stormDate,gageName=gageName)
    # go get the mean flow for this monitor
    df_means = readTotalFlow(filename=meanFile)
    sMeanFlow, meanColor = fRE.constructMeanFlow(tStart=tStart,stormDur=stormDur,dfMeans=df_means)
    # go get the instantaneous flow
    dfFlow = dw.readSliicercsv(filename=flowFile)
    if format:
        dfFlow = dw.formatFlowFile(df=dfFlow,diameterFile=diameterFile,fmname=fmname)
    # pre-compensation period
    pc = tStart - dt.timedelta(days=1)
    # end of recovery period 2
    r2 = tStart + dt.timedelta(days=2,hours=stormDur)
    # pull the instantaneous flow data for the storm period
    sFlow = dfFlow.loc[pc:r2, 'Q (MGD)']
    # calculate the precompensation amount
    pcAdjust = (sFlow[pc:tStart-dt.timedelta(minutes=15)]-sMeanFlow[pc:tStart-dt.timedelta(minutes=15)]).mean()
    # shift mean Flows by this amount
    sMeanFlow += pcAdjust
    grossQ = sFlow[tStart:r2]-sMeanFlow[tStart:r2]
    return(grossQ)


def wetWeather(flowFile,gageFile,dailyFile,hourlyFile,meanFile,fmname,saveDir):
    ######### read in files as pandas dataframes ############
    # FLOW
    dfFlow = dw.readSliicer(filename=flowFile)
    # GAGE NAME
    gagename = dw.findRainGage(filename=gageFile,fmName=fmname)
    # DAILY RAIN
    dfDaily = dw.readRaintxt(filename=dailyFile,useColList=['Date',gagename])
    # HOURLY RIN
    dfHourly = dw.readRaintxt(filename=hourlyFile,useColList=['DateTime',gagename])
    ########## ensure that the flow data and rain data have overlapping dates to ensure no indexing out of range ########
    rainStart, rainEnd = dw.defineDateRange(dfDaily,dfHourly)
    dfDaily = dfDaily.loc[rainStart:rainEnd,:]
    dfHourly = dfHourly.loc[rainStart:rainEnd,:]
    startDate, endDate = dw.defineDateRange(dfDaily,dfFlow)
    dfFlow = dfFlow.loc[startDate:endDate,:]
    dfDaily = dfDaily.loc[startDate:endDate,:]
    dfHourly = dfHourly.loc[startDate:endDate,:]

    # identify storm dates and return storm duration, storm rain total, event duration, and event rain total
    dfStorms = fRE.getStormData(dfDaily=dfDaily,dfHourly=dfHourly,gageName=gagename)

    df_means = readTotalFlow(filename=meanFile)

    # for every storm
    grossVol = []
    delta = 15.0/24/60 # conversion from measurement increments to days for volume calculation
    for k in range(0,len(dfStorms.index)):
        # construct the mean flow for the storm period
        tStart = dfStorms.index[k]
        stormDur = dfStorms.loc[tStart,'Storm Dur']
        sMeanFlow, meanColor = fRE.constructMeanFlow(tStart=tStart,stormDur=stormDur,dfMeans=df_means)
    
        # pre-compensation period
        pc = tStart - dt.timedelta(days=1)
        # end of recovery period 2
        r2 = tStart + dt.timedelta(days=2,hours=stormDur)
        # pull the instantaneous flow data for the storm period
        sFlow = dfFlow.loc[pc:r2, 'Q (MGD)']
        # calculate the precompensation amount
        pcAdjust = (sFlow[pc:tStart-dt.timedelta(minutes=15)]-sMeanFlow[pc:tStart-dt.timedelta(minutes=15)]).values.mean()
        # shift mean Flows by this amount
        sMeanFlow += pcAdjust
        # integrate from storm period to end of r2
        grossVol.extend([delta*np.trapz(sFlow[tStart:r2]-sMeanFlow[tStart:r2])])

    # add grossVol to storms
    dfStorms['Gross Vol'] = grossVol
    dfStorms = dfStorms[dfStorms['Gross Vol'] > 0]  
    saveName = saveDir + '\\' + fmname + '_stormData.csv'
    dfStorms.to_csv(saveName)
    return(dfStorms)

# locates the flow monitor in the file, finds the upstream flow monitors (if they exist), and returns a list of those flow monitors as strings
def findUpstreamFMs(upstreamFile,fmname):
    df = pd.read_csv(upstreamFile,index_col=0)
    usfms = df.loc[fmname,'USFM']
    if usfms=='None':
        usfms = [] #return an empty list
    else:
        usfms = usfms.split(',') # return the list of upstream flow monitors
    
    return(usfms)

def readStormData(fmname,flowDir):
    stormFile = flowDir + '\\' + fmname + '\\' + fmname + '_stormData.csv'
    # does the file exist?
    dfStorm = pd.read_csv(stormFile,index_col=0)
    sGrossII = dfStorm.loc[:,'Gross Vol']
    return(dfStorm,sGrossII)

def findFile(filelist,filekey):
    for aFile in filelist:
        if aFile.startswith(filekey):
            return(aFile)

def upstreamGrossQ(filelist,usfm,flowDirStorm,gageFile,hourlyFile,homeDir,stormDate,diameterFile):
    # find that flow monitor in the csv files
    fmData = findFile(filelist=filelist,filekey=usfm + '_')
    flowFile = flowDirStorm + '\\' + fmData
    gageName = dw.findRainGage(filename=gageFile,fmName=usfm)
    dfHourly = dw.readRaintxt(filename=hourlyFile,useColList=['DateTime',gageName])
    meanFile = homeDir + '\\2018\\Big Creek' + '\\' + usfm + '\\' + usfm + '_meanFlows.csv'
    # get the gross Q for that file
    grossQus = stormGrossQ(stormDate=stormDate,fmname=usfm,gageName=gageName,dfHourly=dfHourly,flowFile=flowFile,meanFile=meanFile,diameterFile=diameterFile,format=format)
    return(grossQus)

def stormNetII(upstreamFile,flowDirStorm,fmName,format,diameterFile,filelist,stormDate,gageFile,hourlyFile,homeDir,flowFile,fmsToSkip):
    gageName = dw.findRainGage(filename=gageFile,fmName=fmName)
    dfHourly = dw.readRaintxt(filename=hourlyFile,useColList=['DateTime',gageName])
    meanFile = homeDir + '\\2018\\Big Creek' + '\\' + fmName+ '\\' + fmName + '_meanFlows.csv'

    grossQ = stormGrossQ(stormDate=stormDate,fmname=fmName,gageName=gageName,dfHourly=dfHourly,flowFile=flowFile,meanFile=meanFile,diameterFile=diameterFile,format=format)
    
    netQ = grossQ.copy()
    usfms = findUpstreamFMs(upstreamFile,fmName)
    if not usfms: #if the list is empty
        # then the gross II is the same as the net and we can just leave it
        pass
    else:
        # for each upstream flow monitor
        for usfm in usfms:
            if usfm in fmsToSkip:
                # find all the upstream monitors of that fm
                U_usfms = findUpstreamFMs(upstreamFile,usfm)
                # if there are no upstream meters of that one
                if not U_usfms: #pass
                    pass
                else:
                    for U_usfm in U_usfms:
                        grossQus = upstreamGrossQ(filelist=filelist,usfm=U_usfm,flowDirStorm=flowDirStorm,gageFile=gageFile,hourlyFile=hourlyFile,homeDir=homeDir,stormDate=stormDate,diameterFile=diameterFile)
                        netQ += -grossQus
            else:
                # find that flow monitor in the csv files
                fmData = findFile(filelist=filelist,filekey=usfm + '_')
                flowFile = flowDirStorm + '\\' + fmData
                gageName = dw.findRainGage(filename=gageFile,fmName=usfm)
                dfHourly = dw.readRaintxt(filename=hourlyFile,useColList=['DateTime',gageName])
                meanFile = homeDir + '\\2018\\Big Creek' + '\\' + usfm + '\\' + usfm + '_meanFlows.csv'
                # get the gross Q for that file
                grossQus = stormGrossQ(stormDate=stormDate,fmname=usfm,gageName=gageName,dfHourly=dfHourly,flowFile=flowFile,meanFile=meanFile,diameterFile=diameterFile,format=format)
                # subtract from downstream value
                netQ += -grossQus
        pass
    return(netQ)

'''
def stormNetII(dfGross,fmName,upstreamFile):
    netVol = []
    # set net volume to gross volume
    gVol = dfGross.loc[fmName,'GrossVol']
    netVol = gVol.copy()
    # find upstream flow monitors
    usfms = findUpstreamFMs(upstreamFile,fmName)
    if not usfms: #if the list is empty
        # then the gross II is the same as the net and we can just leave it
        pass
    else:
        for usfm in usfms:
            usGV = dfGross.loc[usfm,'GrossVol']
            if usGV > 0:
                netVol += - usGV
    return(netVol)

### SHOULD BE WHERE GROSS > 0 ONLY
def netii(upstreamFile,fmname,flowDir):
    # read in the storm data
    dfStorm, sGrossII = readStormData(fmname=fmname,flowDir=flowDir)
    usfms = findUpstreamFMs(upstreamFile=upstreamFile,fmname=fmname)
    sNetII = sGrossII.copy()
    if not usfms: #if the list is empty
        # then the gross II is the same as the net and we can just leave it
        pass
    else:
        for fm in usfms:
            dfStorm_us, sGrossII_us = readStormData(fmname=fm,flowDir=flowDir)
            sNetII += -sGrossII_us
    dfStorm['Net Vol'] = sNetII
    saveName = flowDir + '\\' + fmname + '\\' + fmname + '_stormData.csv'
    dfStorm.to_csv(saveName)
    return(dfStorm)
'''
def findDmax(flowFile,date):
    dfFlow = dw.readSliicercsv(filename=flowFile)
    mask = (dfFlow.index>=date) & (dfFlow.index<date+dt.timedelta(days=1))
    if dfFlow['sdepth (in)'].isna().all():
        sFlow = dfFlow.loc[mask,'y (in)'].sort_values(ascending=False)
    else:
        sFlow = dfFlow.loc[mask,'sdepth (in)'].sort_values(ascending=False)
    if sFlow.empty:
        dmax = float('NaN')
        t_dmax = float('NaN')
        dOneThird = float('NaN')
    else:
        dmax = sFlow.max()
        t_dmax = sFlow.idxmax()
        sFlowHigh = sFlow.iloc[0:int(len(sFlow.index)/3)]
        dOneThird = sFlowHigh.mean()
    return(dmax,t_dmax,dOneThird)

from itertools import groupby


def findStormsOfSize(drt,dailyFile):
    dfDaily = pd.read_csv(dailyFile,sep='\t',index_col=0)
    dfDaily.index = pd.to_datetime(dfDaily.index)
    stormDates = []
    for rg in dfDaily.columns:
        mask = dfDaily[rg] >= drt
        stormDates.extend(dfDaily.index[mask])
    stormDates.sort()
    numRG = [len(list(group)) for key, group in groupby(stormDates)]
    stormDates = list(set(stormDates))
    stormDates.sort()
    s = pd.Series(data=numRG,index=stormDates)
    return(s.index[s>3])
