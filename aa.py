import sys
import os
from os import listdir
from os.path import isfile, join

mypath=sys.argv[1]
both = os.listdir(mypath)
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
onlydir=[]
for f in both:
	if f not in onlyfiles:
		onlydir.append(f)
