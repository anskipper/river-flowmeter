from os import walk

def findTextFiles(readDir):
    d = []
    f = []
    t = []
    c = []
    for (root,dirs,files) in walk(readDir,topdown=True):
        d.extend(dirs)
        f.extend(files)
        for x in f:
            if x.endswith('.txt'):
                t.extend([x])
            elif x.endswith('csv'):
                 c.extend([x])                   
        d = sorted(d)
        t = sorted(t)
        c = sorted(c)
        return(d,t,c)

# read in the flow monitor to usgs site correlation file
def findFileInList(fileList,key):
    for f in fileList:
        if f.startswith(key):
            return(f)
