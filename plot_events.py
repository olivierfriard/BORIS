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



def create_events_plot2(events, all_behaviors, min_t=-1, max_t=-1, output_file_name=""):
    """
    Create gantt charts with barh matplotlib function
    """

    def behav_color(behav):

        if behav in all_behaviors:
            return config.BEHAVIORS_PLOT_COLORS[all_behaviors.index(behav) % len(config.BEHAVIORS_PLOT_COLORS)]
        else:
            return "red"


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
    
    # determine the max number of behaviors
    max_len = 0
    for subject in events:
        max_len = max(max_len, len(events[subject]))
      
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
        
        #ilen = len(ylabels)
        
        ilen = max_len
       
        axs[ax_idx].set_ylim(ymin=0, ymax = (ilen * par1) + par1)
        
        pos = np.arange(par1, ilen * par1 + par1, par1)
        
        axs[ax_idx].set_yticks(pos[:len(ylabels)])
        axs[ax_idx].set_yticklabels(labels, fontdict={"fontsize": 12})
    
        i = 0
        min_time, max_time = 86400, 0

        for ylabel in ylabels:
            for interval in events[subject][ylabel]:
                if interval[0] == interval[1]:
                    start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                    end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0] + point_event_duration))
                    bar_color = "black"
                    min_time = min(min_time, interval[0])
                    max_time = max(max_time, interval[0] + point_event_duration)
                else:
                    start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                    end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[1]))
                    
                    print("ylabel", json.loads(ylabel)[0])
                    
                    bar_color = behav_color(json.loads(ylabel)[0])
                    min_time = min(min_time, interval[0])
                    max_time = max(max_time, interval[1])
    
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

        axs[ax_idx].grid(color = "g", linestyle = ":")
        axs[ax_idx].xaxis_date()
       
        axs[ax_idx].xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))

        axs[ax_idx].invert_yaxis()

    fig.autofmt_xdate()
    plt.tight_layout()
    if output_file_name:
        plt.savefig(output_file_name)
    else:
        plt.show()


'''
def plot_events(self):
    """
    plot events with matplotlib 
    """

    result, selectedObservations = self.selectObservations(MULTIPLE)

    if not selectedObservations:
        return

    # check if almost one selected observation has events
    flag_no_events = True
    for obsId in selectedObservations:
        if self.pj[OBSERVATIONS][obsId][EVENTS]:
            flag_no_events = False
            break
    if flag_no_events:
        QMessageBox.warning(self, programName, "No events found in the selected observations")
        return

    max_media_length = -1
    for obsId in selectedObservations:
        if self.pj[OBSERVATIONS][obsId][TYPE] == MEDIA:
            totalMediaLength = self.observationTotalMediaLength(obsId)
        else: # LIVE
            if self.pj[OBSERVATIONS][obsId][EVENTS]:
                totalMediaLength = max(self.pj[OBSERVATIONS][obsId][EVENTS])[0]
            else:
                totalMediaLength = Decimal("0.0")

        if totalMediaLength == -1:
            totalMediaLength = 0

        max_media_length = max(max_media_length, totalMediaLength)


    if len(selectedObservations) == 1:
        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=totalMediaLength)
    else:
        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=0)

    if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
        QMessageBox.warning(self, programName, "Select subject(s) and behavior(s) to plot")
        return


    if len(selectedObservations) > 1:
        plot_directory = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save events' plots",
                                                                os.path.expanduser("~"),
                                                                options=QFileDialog(self).ShowDirsOnly)

        if not plot_directory:
            return
            
        item, ok = QInputDialog.getItem(self, "Select the file format", "Available formats", ["PNG", "SVG", "PDF", "EPS", "PS"], 0, False)
        if ok and item:
            file_format = item.lower()
        else:
            return

    totalMediaLength = int(totalMediaLength)


    cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

    not_paired_obs_list = []
    for obsId in selectedObservations:
        
        
        if not self.check_state_events_obs(obsId)[0]:
            not_paired_obs_list.append(obsId)
            continue

        o = {}

        for subject in plot_parameters["selected subjects"]:

            o[subject] = {}

            for behavior in plot_parameters["selected behaviors"]:

                if plot_parameters["include modifiers"]:

                    cursor.execute("SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?",
                                   (obsId, subject, behavior))
                    distinct_modifiers = list(cursor.fetchall())

                    for modifier in distinct_modifiers:
                      
                        cursor.execute(("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? "
                                        "ORDER BY observation, occurence"),
                                      (obsId, subject, behavior, modifier[0]))

                        rows = cursor.fetchall()

                        if modifier[0]:
                            behaviorOut = [behavior, modifier[0]]
                        else:
                            behaviorOut = [behavior]

                        behaviorOut_json = json.dumps(behaviorOut)

                        if not behaviorOut_json in o[subject]:
                            o[subject][behaviorOut_json] = []

                        for idx, row in enumerate(rows):
                            if POINT in self.eventType(behavior).upper():
                                o[subject][behaviorOut_json].append([row[0], row[0]])  # for point event start = end

                            if STATE in self.eventType(behavior).upper():
                                if idx % 2 == 0:
                                    try:
                                        o[subject][behaviorOut_json].append([row[0], rows[idx + 1][0]])
                                    except:
                                        if NO_FOCAL_SUBJECT in subject:
                                            sbj = ""
                                        else:
                                            sbj = "for subject <b>{0}</b>".format(subject)
                                        QMessageBox.critical(self, programName,
                                            "The STATE behavior <b>{0}</b> is not paired {1}".format(behaviorOut, sbj))

                else:  # do not include modifiers

                    cursor.execute(("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ? "
                                    "ORDER BY observation, occurence"),
                                  (obsId, subject, behavior))
                    rows = list(cursor.fetchall())

                    if not len(rows) and plot_parameters["exclude behaviors"]:
                        continue

                    if STATE in self.eventType(behavior).upper() and len(rows) % 2:
                        continue

                    behaviorOut_json = json.dumps([behavior])

                    if not behaviorOut_json in o[subject]:
                        o[subject][behaviorOut_json] = []

                    for idx, row in enumerate(rows):
                        if POINT in self.eventType(behavior).upper():
                            o[subject][behaviorOut_json].append([row[0], row[0]])   # for point event start = end

                        if STATE in self.eventType(behavior).upper():
                            if idx % 2 == 0:
                                o[subject][behaviorOut_json].append([row[0], rows[idx + 1][0]])




        print("o", o)
        if len(selectedObservations) == 1:
            create_events_plot2(o, [self.pj[ETHOGRAM][idx]["code"] for idx in sorted_keys(self.pj[ETHOGRAM])],
                                        min_t=float(plot_parameters["start time"]),
                                        max_t=float(plot_parameters["end time"]))
        else:
            create_events_plot2(o, [self.pj[ETHOGRAM][idx]["code"] for idx in sorted_keys(self.pj[ETHOGRAM])],
                                        #min_t=float(plot_parameters["start time"]),
                                        #max_t=float(plot_parameters["end time"]),
                                        output_file_name="{plot_directory}/{obsId}.{file_format}".format(plot_directory=plot_directory,
                                                                                                         obsId=obsId,
                                                                                                         file_format=file_format))
'''







if __name__ == '__main__':
    
  
    all_behaviors = ["aa","bb","ccc","dd","q","zzz","xxx"]
    
    #events = {'No focal subject': {'n': [[0.844], [4.324], [6.58]]},    }
    
    #events = {'No focal subject': {'["a"]': [[0.5,0.5] ,[1.533, 7.539], [9.813, 16.491], [20.349, 58.74]], '["n"]': [[2.964, 2.964]]}}
    events = {'No focal subject': {'["a", "None|None"]': [[0.5,0.5] ,[1.533, 9.813]], '["a", "aaa,ccc|eee"]': [[7.539, 16.491]], '["a", "bbb|ddd"]': [[20.349, 58.74]], '["n", "123"]': [[2.964, 2.964]]}}
    
    
    create_events_plot2(events, all_behaviors, min_t=0, max_t=300)
