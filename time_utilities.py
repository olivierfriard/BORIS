#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2015 Olivier Friard

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""
from __future__ import division

from decimal import *

def getTimeValues( n ):
    '''
    get tick and max scale values for time diagram time axe
    '''
    import math

    if int(n/10**int(math.log10(n))) == round( n/10**int(math.log10(n)) ):
        tick = 10**int(math.log10(n))
        m = (int(n/(10**int(math.log10(n))))+0.5)*10**int(math.log10(n))
    else:
        tick = 10**int(math.log10(n))
        m = (int(n/(10**int(math.log10(n))))+1)*10**int(math.log10(n))

    while m/tick <5:
        tick = tick/2
    
    return tick, m



def time2seconds(time):
    '''
    convert hh:mm:ss.s to number of seconds (decimal)
    '''
    flagNeg = '-' in time
    time = time.replace('-','')

    tsplit= time.split(':')
    
    h, m, s = int( tsplit[0] ), int( tsplit[1] ), Decimal( tsplit[2] )

    if flagNeg:
        return Decimal(-(h * 3600 + m * 60 + s))
    else:
        return Decimal(h * 3600 + m * 60 + s)


def seconds2time(sec):
    '''
    convert seconds to hh:mm:ss.sss format
    '''
    flagNeg = sec < 0
    sec = abs(sec)
    
    hours = 0
   
    minutes = int(sec / 60)
    if minutes >= 60:
        hours = int(minutes /60)
        minutes = minutes % 60

    secs = sec - hours*3600 - minutes * 60
    ssecs = '%06.3f' % secs

    return  "%s%02d:%02d:%s" % ('-' * flagNeg, hours, minutes, ssecs )



def safeFileName(s):
    '''replace characters not allowed in file name by _'''
    fileName = s
    notAllowedChars = ['/','\\']
    for char in notAllowedChars:
        fileName = fileName.replace(char, '_')

    return fileName
