import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import diurnal.findRainEvents as fre 
import diurnal.wetWeather as ww
import diurnal.dryWeather as dw
import datetime as dt
import pandas as pd

# save the quantile and regular diurnals
def saveDiurnals(df_flow,weekCatagory,plotType,saveDir):
#    saveDir = flowDir + flowmeter
    saveName = r'\diurnal-dry-' + weekCatagory + '-' + plotType + '_' + str(df_flow.index.date[0]) +'-' + str(df_flow.index.date[-1])  + '.png'
    plt.savefig(saveDir+saveName)
    print('Figure saved!')

def prettyxTime(ax):
    ticks = ax.get_xticks()
    ax.set_xticks(np.linspace(ticks[0],24*3600,5))
    ax.set_xticks(np.linspace(ticks[0],24*3600,25),minor=True)

def plotDiurnalsAll(df,colorAll,colorMean,figsize,weekCatagory,df_flow,fmName,saveDir):
    fig, ax = plt.subplots()
    df.plot(ax=ax,kind='line',figsize=figsize,legend=False,color=colorAll)
    meanLine = df.mean(axis=1)
    meanLine.plot(ax=ax,kind='line',figsize=figsize,legend=False,color=colorMean,linewidth=3)
    ax.set_title(fmName + ': '+ weekCatagory+' , Dry Weather')
    ax.set_ylabel('Q (MGD)')
    ax.set_ylim(bottom=0,top=1.1*df.max().max())
    ax.set_xlabel('Time of Day')
    prettyxTime(ax)
    ax.grid(which='major',color='xkcd:grey',axis='both')
    saveDiurnals(df_flow=df_flow,weekCatagory=weekCatagory,plotType='all',saveDir=saveDir)
    return(fig,ax)

def plotQuantileDiurnals(df,figsize,color,weekCatagory,upQuantile,lowQuantile,df_flow,fmName,saveDir):
    fig, ax = plt.subplots()
    meanLine = df.mean(axis=1)
    meanLine.plot(ax=ax,kind='line',figsize=figsize,legend=False,color=color,linewidth=2)
    ax.set_title(fmName + ': ' + weekCatagory+' , Dry Weather')
    ax.set_ylabel('Q (MGD)')
    
    ax.set_xlabel('Time of Day')
    ticks = ax.get_xticks()
    ax.set_xticks(np.linspace(ticks[0],24*3600,5))
    ax.set_xticks(np.linspace(ticks[0],24*3600,25),minor=True)
    # get quantiles
    quantUp = df.quantile(upQuantile,axis=1)
    quantUp.plot(ax=ax,style='--',linewidth=2,color=color)
    ax.fill_between(meanLine.index,meanLine,quantUp,alpha=0.2,facecolor=color)
    
    ax.set_ylim(bottom=0,top=1.2*quantUp.max())
    
    quantLow = df.quantile(lowQuantile,axis=1)
    quantLow.plot(ax=ax,style='--',linewidth=2,color=color)
    ax.fill_between(meanLine.index,meanLine,quantLow,alpha=0.2,facecolor=color)
    ax.legend(['mean','95' + r'% or 5' + r'% quantile'])
    ax.grid(which='major',color='xkcd:grey',axis='both')
    saveDiurnals(df_flow=df_flow,weekCatagory=weekCatagory,plotType='quantile',saveDir=saveDir)

    return(fig,ax)

def saveCombined(saveDir,plotType):
    #saveDir = 'H:'+r'\Big Creek'+r'\Subbasin '  + flowmeter
    saveName = r'\weekdayVsweekend_' + plotType + '.png'
    plt.savefig(saveDir+saveName)
    print('Figure saved!')

def plotTogether(meanLine1,meanLine2,gwi,plotgwi,color1,color2,colorg,figsize,plotType,norm,saveDir,fmname):
    fig, ax = plt.subplots()
    meanLine1.plot(ax=ax,kind='line',figsize=figsize,legend=False,color=color1,linewidth=2)
    meanLine2.plot(ax=ax,kind='line',figsize=figsize,legend=False,color=color2,linewidth=2)
    if plotgwi:
        ax.plot([meanLine1.index[0],meanLine1.index[-1]],[gwi,gwi],color=colorg,label='GWI',linewidth=2)
        ax.legend(['Weekday','Weekend','GWI = ' + str(round(gwi,2)) + ' MGD'])
        ax.set_title(fmname + ': Weekday vs. Weekend, Dry Weather')
    else:
        ax.legend(['Weekday','Weekend'])
        ax.set_title(fmname + ': Normalized Sanitary Flow')
    prettyxTime(ax)
    ax.set_ylabel('Q (MGD)')
    if norm: 
        ax.set_ylim(bottom=0,top=2)
    else: 
        ax.set_ylim(bottom=0,top=1.2*max(meanLine1.max(),meanLine2.max()))
    ax.set_xlabel('Time of Day')
    ax.grid(which='major',color='xkcd:grey',axis='both')
    saveCombined(saveDir=saveDir,plotType=plotType)
    return(fig,ax)

# plotting the wet weather with the means
def stormPlot(fmname,stormDate,gageName,meanFile,hourlyFile,flowFile,diameterFile,format):
    dfFlow = dw.readSliicercsv(filename=flowFile)
    if format:
        dfFlow = dw.formatFlowFile(df=dfFlow,diameterFile=diameterFile,fmname=fmname)

    dfHourly = dw.readRaintxt(filename=hourlyFile,useColList=['DateTime',gageName])
    tStart,eventDur,eventRT,stormDur,stormRT = fre.stormAnalyzer(dfHourly,stormDate,gageName)
    dfMeans = ww.readTotalFlow(filename=meanFile)
    sStormMeans,colorMean = fre.constructMeanFlow(tStart,stormDur,dfMeans)

    # timing 
    # pre-compensation
    pc = tStart - dt.timedelta(days=1)
    r2 = tStart + dt.timedelta(hours=stormDur,days=2)

    sFlow = dfFlow.loc[pc:r2,'Q (MGD)']
    if sFlow.empty:
        pass
    else:
        fig,ax = plt.subplots()
        sFlow.plot(ax=ax)
        d = pd.to_datetime(pc.date())
        for color in colorMean:
            mask = (sStormMeans.index>=d) & (sStormMeans.index<=d+dt.timedelta(days=1))
            sStormMeans[mask].plot(ax=ax,color=color)
            d += dt.timedelta(days=1)
        ax.set_title(fmname)

# candlestick graphs
# daterange = (startDate,endDate)
def makeCandlesticks(flowFile,homeDir,fmname,dfrain,gagename,daterange):
    ############## FORMAT DATA ##############################
    # read in data file as dataframes
    dfAll = dw.readSliicer(flowFile)
    # chop them up
    df = dfAll.loc[daterange[0]:daterange[1],:]
    # convert rain to a list
    rain = list(dfrain.loc[daterange[0]:daterange[1],gagename].values)
    # reorganize flow data
    df = dw.reorganizeFlowData(df=df,colVal='Q (MGD)')
    ################## CREATE LABELS ###########################
    # create data frame of dates from the original dataframe columns
    df2 = pd.DataFrame({'original': df.columns})
    # convert from string into datetime
    df2['original']=pd.to_datetime(df2.original)
    # set a column for the labels to the day value as a string
    df2['label']=df2['original'].dt.strftime('%d')
    # create a separate column that has the day as an integer
    df2['dayonly']=df2['original'].dt.day
    # find the first day of each month and set it to format Jan 1, Feb 1, etc.
    mask = df2['dayonly']<2
    df2.loc[mask,'label'] = df2.loc[mask,'original'].dt.strftime('%b')
    #set label colors
    df2['rain'] = rain
    # create list of rain indices for plotting
    rainIndx = df2.index[df2['rain']>0.5].tolist()
    ################# CREATE FIGURE #######################
    fig,ax = plt.subplots(figsize=(20,4))
    # plot
    bp = ax.boxplot(df.values,
                    labels=df2['label'],
                    sym='+',
                    patch_artist=True)

    # defaults are weekday colors - xkcd:charcoal for whiskers and fliers, beige for dry weather
    plt.setp(bp['boxes'],color='xkcd:beige')
    plt.setp(bp['whiskers'],color='xkcd:grey')
    plt.setp(bp['fliers'],color='xkcd:grey')
    plt.setp(bp['medians'],color='xkcd:grape',linewidth=1.2)

    # add light grid
    ax.yaxis.grid(True,linestyle='-',
              which='major',
              color='xkcd:light grey',
              alpha=0.5)
    ax.xaxis.grid(True,linestyle='-',
              which='major',
              color='xkcd:light grey',
              alpha=0.5)
    ax.set_ylabel('Q (MGD)')
    top = round(1.1*dfAll.max().max())
    ax.set_ylim(0, top)
    ax.set_title(str(daterange[0].strftime('%b %Y'))+ ' - ' 
             + str(daterange[1].strftime('%b %Y')))

    # color for rain
    count = 0
    for box in bp['boxes']:
        if count in rainIndx:
            box.set_facecolor(color='xkcd:powder blue')
        count +=1
    
    # add rain labels
    numBoxes = len(df2.label)
    pos = np.arange(numBoxes) + 1
    # get the rain values
    upperLabels = rain
    count = 0
    for tick, label in zip(range(numBoxes), ax.get_xticklabels()):
        if count in rainIndx:
            ax.text(pos[tick], top - (top*0.08), upperLabels[tick],
                horizontalalignment='center', size='medium',
                color='xkcd:medium blue')
        count+=1

    saveName = homeDir + '\\Big Creek\\' + fmname + '\\'+ fmname +'_' + str(daterange[0].date()) + '-' + str(daterange[1].date()) + '.png'
    plt.savefig(saveName)

def dftoHeatmap(df,numsplits,figsize,saveDir):
    iSave = []
    fms = []
    for k in range(0,numsplits):
        if k == 0:
            indStart = 0
            indEnd = int(len(df)/numsplits)
        else:
            indStart = k*int(len(df)/numsplits)+1
            indEnd = (k+1)*int(len(df)/numsplits)
        ii = df.iloc[indStart:indEnd,0]
        for j in range(0,len(df.columns)):
            if j>0:
                ii = np.vstack((ii,df.iloc[indStart:indEnd,j].values))
        iSave.extend([ii])
        fms.extend([list(df.index[indStart:indEnd])])
    
        # plot for each split
        fig,ax = plt.subplots(figsize=figsize)
        plt.pcolor(ii.T, cmap='YlOrRd',vmin = 0, vmax=3)
        cb = plt.colorbar()
        cb.ax.set_title('Net I&I')
    
        # format axis
        ax.set_xticks(range(0,len(df.columns)+1))
        ax.set_yticks(range(0,len(fms[k])+1))
        ax.grid(b=True,color='xkcd:blue grey',which='major',linewidth=0.5,
            alpha = 0.5)
        # Hide major tick labels
        ax.xaxis.set_major_formatter(ticker.NullFormatter())

        # Customize minor tick labels
        ax.xaxis.set_minor_locator(ticker.FixedLocator(list(
            np.linspace(0.5,len(df.columns)-0.5,len(df.columns)))))
    
        ax.xaxis.set_minor_formatter(ticker.FixedFormatter(list(df.columns)))

        ax.yaxis.set_major_formatter(ticker.NullFormatter())
        ax.yaxis.set_minor_locator(ticker.FixedLocator(list(
            np.linspace(0.5,len(df.index)-0.5,len(df.index)))))
        ax.yaxis.set_minor_formatter(ticker.FixedFormatter(list(df.index)))
    
        saveName = saveDir + 'heatmap_' + fms[k][0] + '-' + fms[k][-1]+ '.png'
        plt.savefig(saveName)
        plt.close(fig)