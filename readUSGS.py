'''
Take in USGS files of flowrate, river stage, resevoir elevation and/or precipitation data
'''
#imports
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np

# read text file into a dataframe with pandas
site_no = '02335450'
pullstart = dt.datetime(2018,12,1).strftime('%Y%m%d')
pullend = dt.datetime(2019,6,3).strftime('%Y%m%d')
# depth always reported as GAGE DEPTH

def makeFilename(site_no,startdate,enddate):
    tfile = r'\USGS' + site_no + '_15min_' + startdate + '-' + enddate + '.txt'
    return(tfile)

homeDir = 'H:' + r'\Big Creek' +r'\USGS River' 
tfile = makeFilename(site_no,pullstart,pullend)

# input is a text file from USGS
# output is a dataframe with datetime as the index and 
def readUSGS(filename, sep, headNum, iCol):
    df = pd.read_csv(filename, sep='	',header=headNum,index_col=iCol)
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

df_river = readUSGS(filename=homeDir+tfile,sep='   ',headNum=28,iCol=2)

flowDir = 'P:'+r'\PW-WATER SERVICES'+r'\TECHNICAL SERVICES'+r'\Anna'
flowmeter = r'\BC19'
fmName = 'BC19'
extratext = '_28660533'
flowFile = flowDir +  flowmeter + extratext + '.txt'

#input is a text file from sliicer
#output is a dataframe with indices in datetime and columns of depth, velocity and flowrate respectively
def readSliicer(filename):
    df = pd.read_csv(filename,sep='	',header=2, index_col=0,names=['depth of flow','v','Q'])
    df.index = pd.to_datetime(df.index)
    return(df)

df_flow = readSliicer(flowFile)

# define the date range of inquiry based on the input ranges
def defineDateRange(df1,df2):
    start1 = df1.index[0]
    start2 = df2.index[0]
    if start1<=start2:
        start = start2 #pick the later date
    else:
        start = start1
    end1 = df1.index[-1]
    end2 = df2.index[-1]
    if end1<=end2:
        end = end1
    else:
        end = end2
    return(start,end)

startDate, endDate = defineDateRange(df_flow,df_river)

def findRiverDatum(site_no,datumFile,datumName):
    df = pd.read_csv(datumFile,',',index_col=0)
    riverDatum = df.loc[int(site_no),datumName]
    return(riverDatum)

datumFile = homeDir+r'\USGSID_datum.txt'
riverDatum = findRiverDatum(site_no,datumFile,'NAVD88')

def findManholeDatum(fmName,datumFile):
    df = pd.read_csv(datumFile,',',index_col=0)
    rimEl = df.loc[fmName,'Rim Elevation'] #ft
    bottomEl = df.loc[fmName,'Bottom Elevation'] #ft
    pipeHeight = df.loc[fmName,'Pipe Height'] #in
    return(rimEl,bottomEl,pipeHeight)

sewerDatumFile = homeDir + r'\FID_datum.txt'
rimEl,bottomEl,pipeHeight = findManholeDatum(fmName,sewerDatumFile)
offset = 0

def plotDepthTimeSeries(sewer,river,flowmeter):
    global rimEl 
    global bottomEl 
    global pipeHeight
    global riverDatum
    global site_no
    global startDate
    global endDate
    global offset

    fig,ax = plt.subplots()

    #plot pipe info
    ax.plot([startDate,endDate],[rimEl+offset,rimEl+offset],color='xkcd:moss',label='rim elevation')
    ax.plot([startDate,endDate],[bottomEl+offset,bottomEl+offset],color='xkcd:charcoal',label='pipe')
    ax.plot([startDate,endDate],[bottomEl+offset+pipeHeight/12,bottomEl+offset+pipeHeight/12],color='xkcd:charcoal')

    color_r = 'xkcd:lightblue'
    river.plot(ax=ax,kind='line',figsize=(12,7),color=color_r,label='river @'+site_no)

    #plot sewer
    color_s = 'xkcd:bright purple'
    ax.set_ylabel('Elevation (ft)')
    ax.set_xlabel('Date')
    sewer.plot(ax=ax,kind='line',figsize=(12,7),color=color_s,title = flowmeter + ' USGS ' + site_no,label='sewer')

    ax.legend()
    return(fig,ax)
#def saveFigure(ax,saveDir,saveName)

s = df_flow.loc[startDate:endDate,['depth of flow']]/12 + bottomEl + offset
r = df_river.loc[startDate:endDate,['river elevation']]+riverDatum
fig1,ax1 = plotDepthTimeSeries(sewer=s,river=r,flowmeter=fmName)
saveDir = homeDir
saveName = flowmeter + '_USGS'+ site_no + '_' + startDate.strftime('%Y%m%d') + '-' + endDate.strftime('%Y%m%d') + '.png'
plt.savefig(saveDir+saveName)