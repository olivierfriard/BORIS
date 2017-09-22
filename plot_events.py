#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2017 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""


"""
GANTT Chart with Matplotlib
Sukhbinder
Inspired from
<div class="embed-theclowersgroup"><blockquote class="wp-embedded-content"><a href="http://www.clowersresearch.com/main/gantt-charts-in-matplotlib/">Gantt Charts in Matplotlib</a></blockquote><script type="text/javascript"><!--//--><![CDATA[//><!--        !function(a,b){"use strict";function c(){if(!e){e=!0;var a,c,d,f,g=-1!==navigator.appVersion.indexOf("MSIE 10"),h=!!navigator.userAgent.match(/Trident.*rv:11./),i=b.querySelectorAll("iframe.wp-embedded-content");for(c=0;c<i.length;c++)if(d=i[c],!d.getAttribute("data-secret")){if(f=Math.random().toString(36).substr(2,10),d.src+="#?secret="+f,d.setAttribute("data-secret",f),g||h)a=d.cloneNode(!0),a.removeAttribute("security"),d.parentNode.replaceChild(a,d)}else;}}var d=!1,e=!1;if(b.querySelector)if(a.addEventListener)d=!0;if(a.wp=a.wp||{},!a.wp.receiveEmbedMessage)if(a.wp.receiveEmbedMessage=function(c){var d=c.data;if(d.secret||d.message||d.value)if(!/[^a-zA-Z0-9]/.test(d.secret)){var e,f,g,h,i,j=b.querySelectorAll('iframe[data-secret="'+d.secret+'"]'),k=b.querySelectorAll('blockquote[data-secret="'+d.secret+'"]');for(e=0;e<k.length;e++)k[e].style.display="none";for(e=0;e<j.length;e++)if(f=j[e],c.source===f.contentWindow){if(f.removeAttribute("style"),"height"===d.message){if(g=parseInt(d.value,10),g>1e3)g=1e3;else if(200>~~g)g=200;f.height=g}if("link"===d.message)if(h=b.createElement("a"),i=b.createElement("a"),h.href=f.getAttribute("src"),i.href=d.value,i.host===h.host)if(b.activeElement===f)a.top.location.href=d.value}else;}},d)a.addEventListener("message",a.wp.receiveEmbedMessage,!1),b.addEventListener("DOMContentLoaded",c,!1),a.addEventListener("load",c,!1)}(window,document);//--><!]]></script><iframe sandbox="allow-scripts" security="restricted" src="http://www.clowersresearch.com/main/gantt-charts-in-matplotlib/embed/" width="600" height="338" title="“Gantt Charts in Matplotlib” — The Clowers Group" frameborder="0" marginwidth="0" marginheight="0" scrolling="no" class="wp-embedded-content"></iframe></div>
"""
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import matplotlib.dates
from matplotlib.dates import MICROSECONDLY, SECONDLY, MINUTELY, HOURLY, WEEKLY, MONTHLY, DateFormatter, rrulewrapper, RRuleLocator
import numpy as np
import json
import config



def CreateGanttChart(events, all_behaviors, min_t=-1, max_t=-1, output_file_name=""):
    """
        Create gantt charts with matplotlib
        Give file name.
    """

    def behav_color(behav):
        try:
            return config.BEHAVIORS_PLOT_COLORS[all_behaviors.index(behav) % len(config.BEHAVIORS_PLOT_COLORS)]
        except:
            return 'red'


    par1 = 1

    bar_height = 0.5

    point_event_duration = 0.010
    
    init = dt.datetime(2017,9,21)

    if len(events) > 1:
        fig, axs = plt.subplots(figsize=(20,8), nrows=len(events), ncols=1, sharex=True)
    else:
        fig, ax = plt.subplots(figsize=(20,8), nrows=len(events), ncols=1, sharex=True)
        axs = np.ndarray(shape=(1), dtype=type(ax))
        axs[0] = ax
       
      
    for ax_idx, subject in enumerate(sorted(events.keys())):
        
        axs[ax_idx].set_title(subject, fontsize=14)

        observed_behaviors = []
        labels = []
        for k in sorted(events[subject].keys()):
            behav_modif = json.loads(str(k))
            if len(behav_modif) > 1:
                behav, modif = behav_modif
                labels.append("{} ({})".format(behav, modif))
            else:
                behav = behav_modif[0]
                labels.append(behav)
            
        ylabels = [str(k) for k in sorted(events[subject].keys())]
        
        print(ylabels)
        
        ilen = len(ylabels)
       
        axs[ax_idx].set_ylim(ymin=0, ymax = (ilen * par1) + par1)
        
        pos = np.arange(par1, ilen * par1 + par1, par1)
        
        axs[ax_idx].set_yticks(pos)
        axs[ax_idx].set_yticklabels(labels, fontdict={'fontsize':12})
        #plt.setp(labelsy, fontsize=10)
    
        i = 0
        min_time, max_time = 86400, 0

        #axs[ax_idx].text( matplotlib.dates.date2num(init + dt.timedelta(seconds=1)), (i * par1) + par1 - par1, "TEST",fontsize=20, color='black',)
        for ylabel in ylabels:
            for interval in events[subject][ylabel]:
                if len(interval) == 1:
                    start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                    end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0] + point_event_duration))
                    bar_color = "black"
                    min_time = min(min_time, interval[0])
                    max_time = max(max_time, interval[0] + point_event_duration)
                else:
                    start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                    end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[1]))
                    bar_color = behav_color(ylabel)
                    min_time = min(min_time, interval[0])
                    max_time = max(max_time, interval[1])
    
                
                print((i * par1) + par1)
                
                axs[ax_idx].barh((i * par1) + par1, end_date - start_date, left=start_date, height=bar_height,
                                 align='center', edgecolor=bar_color, color=bar_color, alpha = 1)
            i += 1
    

        #axs[ax_idx].axis('tight')
    
                
        if min_t == -1:
            min_time = 0
        else:
            min_time = min_t
            
        if max_t != -1:
            max_time = max_t
        
        axs[ax_idx].set_xlim(xmin = matplotlib.dates.date2num(init + dt.timedelta(seconds=min_time)),
                    xmax = matplotlib.dates.date2num(init + dt.timedelta(seconds=max_time + 1)))
    
        axs[ax_idx].grid(color = 'g', linestyle = ':')
        axs[ax_idx].xaxis_date()
    
    
        #rule = rrulewrapper(MINUTELY, interval=10)
        duration = max_time + 1 - min_time
        
        print("duration", duration)
        
       
        
        
        '''if duration <= 300:
            loc = RRuleLocator(rrulewrapper(SECONDLY, interval=10))
        else:
            loc = RRuleLocator(rrulewrapper(MINUTELY, interval=round((duration/60)//10)))
            
        print(loc)

        axs[ax_idx].xaxis.set_major_locator(loc)
        '''
          
  

        
        axs[ax_idx].xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
        

        #axs[ax_idx].set_xticks(pos)
        #axs[ax_idx].set_xticklabels(ylabels)

    
        #font = font_manager.FontProperties(size='small')
        #axs[ax_idx].legend(loc=1,prop=font)
    
        axs[ax_idx].invert_yaxis()

    fig.autofmt_xdate()
    #plt.savefig('gantt.svg')
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    
 
    events = {"Subject 1":
               {'azzzzza': [ [8, 100],
                          [2.456, 3.895],
                          [5.444,6.777]
                          ],
                    'bb':[ [5],[6],
                          [6.8, 7.9],
                          [5.2, 6.3]
                          ],
                'ccc' : [[50],[1,2],[3,4],[5,147]],
                'dd': [[1,7]]
                },
            "Subject 2": {"q":[[1,2],[3,4],[5,17]],
            "q":[[20,29],[33,44.969]],
                
                },
                "subject 3":{"bb":[[1,2],[3,4],[5,205]]}
            }
    
    all_behaviors = ["aa","bb","ccc","dd","q","zzz","xxx"]
    
    #events = {'No focal subject': {'n': [[0.844], [4.324], [6.58]]},    }
    
    events = {'No focal subject': {'["a"]': [[1.533, 7.539], [9.813, 16.491], [20.349, 58.74]], '["n"]': [[2.964, 2.964]]}}
    events = {'No focal subject': {'["a", "None|None"]': [[1.533, 9.813]], '["a", "aaa,ccc|eee"]': [[7.539, 16.491]], '["a", "bbb|ddd"]': [[20.349, 58.74]], '["n", "123"]': [[2.964, 2.964]]}}
    
    
    CreateGanttChart(events, all_behaviors, min_t=0, max_t=300)
