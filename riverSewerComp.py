from diurnal import dryWeather as dw
from diurnal import wetWeather as ww
from diurnal import fileIO as fio
from diurnal import usgs
from os import makedirs
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np

# FILE LOCATIONS
flowDir = 'P:\\PW-WATER SERVICES\\TECHNICAL SERVICES\\Anna\\Storm Analysis\\FlowData_20180421_20180427'
meanDir = 'P:\\PW-WATER SERVICES\\TECHNICAL SERVICES\\Anna\\2018\\Big Creek'
usgsDir = 'H:\\Big Creek\\USGS River\\Nov12th'
folderMade = False

stormDate = dt.datetime(2018,11,12)
tStart = dt.datetime(2018,11,10)
tEnd = dt.datetime(2018,11,16,23,45)

monthDict = {1: 'Jan',
            2: 'Feb',
            3: 'March',
            4: 'April',
            5: 'May',
            6: 'June',
            7: 'July',
            8: 'Aug',
            9: 'Sep',
            10: 'Oct',
            11: 'Nov',
            12: 'Dec',}

seasonDict = {1: 'winter',
            2: 'winter',
            3: 'spring',
            4: 'spring',
            5: 'spring',
            6: 'summer',
            7: 'summer',
            8: 'summer',
            9: 'summer',
            10: 'winter',
            11: 'winter',
            12: 'winter',}

seasonClrM = {'winter' : 'GnBu',
            'spring' : 'RdPu',
            'summer': 'YlOrRd'}

seasonClr = {'winter' : 'xkcd:turquoise',
            'spring' : 'xkcd:pinkish purple',
            'summer': 'xkcd:scarlet'}


# find the flow files
flow_folders,flow_txt,flow_csv = fio.findTextFiles(readDir=flowDir)
# find the USGS files
usgs_folders,usgs_txt,usgs_csv = fio.findTextFiles(readDir=usgsDir)

# the number of header rows
headNums = {'2335580' : 29,
            '2335700' : 29,
            '2335757' : 27,
            '2335790' : 30,
            '2335450' : 27,
            '2335810' : 29}
columnsPlot = {'2335580' : 'river elevation',
            '2335700' : 'river elevation',
            '2335757' : 'river elevation',
            '2335790' : 'river elevation',
            '2335450' : 'river elevation',
            '2335810' : 'resevoir elevation'}

# create empty dictionary for usgs dataframes
usgsDict = {}

# read in the correlation between flow monitors and usgs sits
fm2usgs = usgs.readFMtoUSGS(fileList=usgs_csv,usgsDir=usgsDir)

# create a directory called Figures if it doesn't exist already
if 'Figures' not in usgs_folders:
    #make the directory
    makedirs(usgsDir+"\\"+'Figures')
saveDir = usgsDir+"\\"+'Figures'
    

# for all the flow monitors
for fmData in flow_csv:
    # get the flowmonitor name
    fmname = fmData.split('_')[0]
    if fmname=='BC26':
        pass
    else:
        print(fmname)
        # read in flow monitor data
        flowFile = flowDir + "\\" + fmData
        # dfFlow columns: ['sdepth (in)','y (in)','v (ft/s)','Q (MGD)'], dfFlow index = 'Datetime'
        dfFlow = dw.readSliicercsv(filename=flowFile)
    
        # go grab the mean data for the file
        meanFile = meanDir + '\\' + fmname + '\\' + fmname + '_meanFlows.csv'
        dfMeans = ww.readTotalFlow(meanFile)
        meanFlow = usgs.constructMeanFlow(tStart,tEnd,dfMeans)

        # find usgs site
        site = str(fm2usgs.loc[fmname,'USGSID']) #formatted as '2335580' for example
        #isclosest = fm2usgs.loc[fmname,'Closest']
        #site = '2335790'
        # find the file
        # if it's already in the dictionary, go get it
        if site in usgsDict:
            dfRiver = usgsDict[site]
        # otherwise find it and add it to the dictionary
        else:
            for riverFile in usgs_txt:
                if riverFile.startswith('USGS0'+site):
                    readRiver = usgsDir + '\\' + riverFile
                    dfRiver = usgs.readUSGS(filename=readRiver,headerNum=headNums[site])
                    usgsDict[site] = dfRiver
    # dfRiver columns can vary, but the flow will be 'Q-river' [cfs] and stage will be 'river-elevation' [ft]

        # for all the flow monitors, plot the river stage in feet and the flow rate of the pipe on different y axes
        dfFlow['net'] = dfFlow['Q (MGD)'].values - meanFlow.values
        mask = dfFlow['net']<0
        dfFlow.loc[mask,'net'] = 0

        fig,ax = plt.subplots()
        flowColor = seasonClr[seasonDict[dfFlow.index[0].month]]
        ax.set_title(fmname)
        ax.set_ylabel('Net Q (MGD)',color=flowColor,
               rotation='vertical',fontsize=14)
        ax.tick_params(axis='y',labelcolor=flowColor)
        dfFlow['net'].plot(kind='line',ax=ax,fontsize=14,color=flowColor)

        ax2 = ax.twinx()
        ax2.set_ylabel(columnsPlot[site],color='xkcd:charcoal',
               rotation='vertical',fontsize=14)
        ax2.tick_params(axis='y',labelcolor='xkcd:charcoal')
        dfRiver[columnsPlot[site]].plot(kind='line',ax=ax2,fontsize=14,color='xkcd:charcoal')
        ax2.set_xlabel('Date')

        saveName = '\\USGS0' + site + '_' + fmname + '_' + str(stormDate.date()) + '.png'
        plt.savefig(saveDir+saveName)
        plt.close(fig)