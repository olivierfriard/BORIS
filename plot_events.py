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
import utilities


def create_events_plot2(events,
                        all_behaviors,
                        all_subjects,
                        exclude_behaviors_wo_events=True, min_time=-1, max_time=-1, output_file_name="",
                        plot_colors=config.BEHAVIORS_PLOT_COLORS):
    """
    Create gantt charts with barh matplotlib function
    """

    def behav_color(behav):
        """
        return color corresponding to behavior
        if color not found returns "darkgray"

        see BEHAVIORS_PLOT_COLORS list in config.py
        """

        if behav in all_behaviors:
            return utilities.behavior_color(plot_colors, all_behaviors.index(behav))
        else:
            return "darkgray"

    par1 = 1
    bar_height = 0.5
    point_event_duration = 0.010
    init = dt.datetime(2017, 1, 1)

    if len(events) > 1:
        fig, axs = plt.subplots(figsize=(20, 8), nrows=len(events), ncols=1, sharex=True)
    else:
        fig, ax = plt.subplots(figsize=(20, 8), nrows=len(events), ncols=1, sharex=True)
        axs = np.ndarray(shape=(1), dtype=type(ax))
        axs[0] = ax

    # determine the max number of behaviors
    max_len = 0
    observed_behaviors_modifiers_json = []
    for subject in events:
        max_len = max(max_len, len(events[subject]))
        observed_behaviors_modifiers_json = list(set(observed_behaviors_modifiers_json + list(events[subject].keys())))

    # order subjects
    try:
        ordered_subjects = [x[1] for x in sorted(list(zip([all_subjects.index(x) for x in sorted(list(events.keys()))], sorted(list(events.keys())))))]
    except ValueError:
        ordered_subjects = sorted(list(events.keys()))

    for ax_idx, subject in enumerate(ordered_subjects):

        axs[ax_idx].set_title(subject, fontsize=14)
        labels_str, ylabels = [], []
        flag_modifiers = False

        for behav1 in all_behaviors:
            for bm_json in (events[subject] if exclude_behaviors_wo_events else observed_behaviors_modifiers_json):
                if behav1 == json.loads(bm_json)[0]:
                    ylabels.append(bm_json) 
                    behav_modif = json.loads(bm_json)
                    if len(behav_modif) > 1:
                        behav, modif = behav_modif
                        labels_str.append("{} ({})".format(behav, modif))
                        flag_modifiers = True
                    else:
                        behav = behav_modif[0]
                        labels_str.append(behav)

        ilen = max_len
        axs[ax_idx].set_ylim(ymin=0, ymax = (ilen * par1) + par1)
        pos = np.arange(par1, ilen * par1 + par1, par1)
        axs[ax_idx].set_yticks(pos[:len(ylabels)])
        axs[ax_idx].set_yticklabels(labels_str, fontdict={"fontsize": 12})
        
        if flag_modifiers:
            axs[ax_idx].set_ylabel("Behaviors (modifiers)", fontdict={"fontsize": 12})
        else:
            axs[ax_idx].set_ylabel("Behaviors", fontdict={"fontsize": 12})

        i = 0
        #min_time, max_time = 86400, 0

        for ylabel in ylabels:
            if ylabel in events[subject]:
                for interval in events[subject][ylabel]:
                    if interval[0] == interval[1]:
                        start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                        end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0] + point_event_duration))
                        bar_color = "black"
                        #min_time = min(min_time, interval[0])
                        #max_time = max(max_time, interval[0] + point_event_duration)
                    else:
                        start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                        end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[1]))
                        bar_color = behav_color(json.loads(ylabel)[0])
                        #min_time = min(min_time, interval[0])
                        #max_time = max(max_time, interval[1])
                    try:
                        axs[ax_idx].barh((i * par1) + par1, end_date - start_date, left=start_date, height=bar_height,
                                         align="center", edgecolor=bar_color, color=bar_color, alpha = 1)
                    except ValueError:
                        return {"error code": 1, "msg": "Invalid color name: <b>{}</b>".format(bar_color)}
            i += 1

        #print("min_time",min_time)
        #print("max_time",max_time)

        #axs[ax_idx].axis('tight')
        '''
        if min_t == -1:
            min_time = 0
        else:
            min_time = min_t

        if max_t != -1:
            max_time = max_t
        '''

        #print("min_time",min_time)
        #print("max_time",max_time)
        #print()

        axs[ax_idx].set_xlim(xmin = matplotlib.dates.date2num(init + dt.timedelta(seconds=min_time)),
                             xmax = matplotlib.dates.date2num(init + dt.timedelta(seconds=max_time + 1)))

        axs[ax_idx].grid(color = "g", linestyle = ":")
        axs[ax_idx].xaxis_date()
       
        axs[ax_idx].xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
        axs[ax_idx].set_xlabel("Time (HH:MM:SS)", fontdict={"fontsize": 12})

        axs[ax_idx].invert_yaxis()

    fig.autofmt_xdate()
    plt.tight_layout()
    if output_file_name:
        plt.savefig(output_file_name)
    else:
        plt.show()

    return {"error code": 0, "msg": ""}

if __name__ == '__main__':
  
    all_behaviors = ["p","s","a","n"]
    all_subjects = ["No focal subject", "subj 2", "subj 1"]
    #events = {'No focal subject': {'["p"]': [], '["s"]': [], '["a"]': [[47.187, 56.107]], '["n"]': []}, 'subj 2': {'["p"]': [[10.62, 10.62], [11.3, 11.3], [12.044, 12.044], [13.228, 13.228]], '["s"]': [[31.852, 37.308]], '["a"]': [], '["n"]': []}, 'subj 1': {'["p"]': [[7.116, 7.116], [8.5, 8.5], [9.42, 9.42]], '["s"]': [[19.476, 44.564]], '["a"]': [[15.787, 24.01]], '["n"]': [[11.459, 11.459], [17.611, 17.611]]}}
    events = {'No focal subject': {'["a", "None|None"]': [[47.187, 56.107]]}, 'subj 2': {'["p"]': [[10.62, 10.62], [11.3, 11.3], [12.044, 12.044], [13.228, 13.228]], '["s"]': [[31.852, 37.308]]}, 'subj 1': {'["p"]': [[7.116, 7.116], [8.5, 8.5], [9.42, 9.42]], '["s"]': [[19.476, 44.564]], '["a", "None"]': [[15.787, 24.01]], '["n", "123"]': [[11.459, 11.459]], '["n", "456"]': [[17.611, 17.611]]}}

    create_events_plot2(events, all_behaviors, all_subjects, exclude_behaviors_wo_events=False, min_time=0, max_time=100)
