#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard

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
import matplotlib.transforms as mtransforms
import matplotlib.dates
from matplotlib.dates import MICROSECONDLY, SECONDLY, MINUTELY, HOURLY, WEEKLY, MONTHLY, DateFormatter, rrulewrapper, RRuleLocator
import numpy as np
import json
from config import *
import utilities



def plot_time_ranges(pj, time_format, plot_colors, obs, obsId, minTime, videoLength, excludeBehaviorsWithoutEvents, line_width):
    """
    create "hlines" matplotlib plot
    used by plot_event function (legacy)
    """

    def on_draw(event):
        # http://matplotlib.org/faq/howto_faq.html#move-the-edge-of-an-axes-to-make-room-for-tick-labels
        bboxes = []
        for label in labels:
            bbox = label.get_window_extent()
            bboxi = bbox.inverse_transformed(fig.transFigure)
            bboxes.append(bboxi)

        bbox = mtransforms.Bbox.union(bboxes)
        if fig.subplotpars.left < bbox.width:
            fig.subplots_adjust(left=1.1*bbox.width)
            fig.canvas.draw()
        return False

    LINE_WIDTH = line_width
    all_behaviors, observedBehaviors = [], []
    maxTime = 0  # max time in all events of all subjects

    # all behaviors defined in project without modifiers
    all_project_behaviors = [pj[ETHOGRAM][idx]["code"] for idx in utilities.sorted_keys(pj[ETHOGRAM])]
    all_project_subjects = [NO_FOCAL_SUBJECT] + [pj[SUBJECTS][idx]["name"] for idx in utilities.sorted_keys(pj[SUBJECTS])]

    for subject in obs:

        for behavior_modifiers_json in obs[subject]:

            behavior_modifiers = json.loads(behavior_modifiers_json)

            if not excludeBehaviorsWithoutEvents:
                observedBehaviors.append(behavior_modifiers_json)
            else:
                if obs[subject][behavior_modifiers_json]:
                    observedBehaviors.append(behavior_modifiers_json)

            if not behavior_modifiers_json in all_behaviors:
                all_behaviors.append(behavior_modifiers_json)

            for t1, t2 in obs[subject][behavior_modifiers_json]:
                maxTime = max(maxTime, t1, t2)

        observedBehaviors.append("")

    lbl = []
    if excludeBehaviorsWithoutEvents:
        for behav_modif_json in observedBehaviors:
            
            if not behav_modif_json:
                lbl.append("")
                continue
            
            behav_modif = json.loads(behav_modif_json)
            if len(behav_modif) == 2:
                lbl.append("{0} ({1})".format(behav_modif[0], behav_modif[1]))
            else:
                lbl.append(behav_modif[0])

    else:
        all_behaviors.append('[""]') # empty json list element
        for behav_modif_json in all_behaviors:
            
            behav_modif = json.loads(behav_modif_json)
            if len(behav_modif) == 2:
                lbl.append("{0} ({1})".format(behav_modif[0], behav_modif[1]))
            else:
                lbl.append(behav_modif[0])
        lbl = lbl[:] * len(obs)


    lbl = lbl[:-1]  # remove last empty line

    fig = plt.figure(figsize=(20, 10))
    fig.suptitle("Time diagram of observation {}".format(obsId), fontsize=14)
    ax = fig.add_subplot(111)
    labels = ax.set_yticklabels(lbl)

    ax.set_ylabel("Behaviors")

    if time_format == HHMMSS:
        fmtr = dates.DateFormatter("%H:%M:%S") # %H:%M:%S:%f
        ax.xaxis.set_major_formatter(fmtr)
        ax.set_xlabel("Time (hh:mm:ss)")
    else:
        ax.set_xlabel("Time (s)")

    plt.ylim(len(lbl), -0.5)

    if not videoLength:
        videoLength = maxTime

    if pj[OBSERVATIONS][obsId]["time offset"]:
        t0 = round(pj[OBSERVATIONS][obsId]["time offset"] + minTime)
        t1 = round(pj[OBSERVATIONS][obsId]["time offset"] + videoLength + 2)
    else:
        t0 = round(minTime)
        t1 = round(videoLength)
    subjectPosition = t0 + (t1 - t0) * 0.05

    if time_format == HHMMSS:
        t0d = datetime.datetime(1970, 1, 1, int(t0 / 3600), int((t0 - int(t0 / 3600) * 3600) / 60), int(t0 % 60), round(round(t0 % 1, 3) * 1000000))
        t1d = datetime.datetime(1970, 1, 1, int(t1 / 3600), int((t1 - int(t1 / 3600) * 3600) / 60), int(t1 % 60), round(round(t1 % 1, 3) * 1000000))
        subjectPositiond = datetime.datetime(1970, 1, 1, int(subjectPosition / 3600), int((subjectPosition - int(subjectPosition / 3600) * 3600) / 60), int(subjectPosition % 60), round(round(subjectPosition % 1, 3) * 1000000))

    if time_format == S:
        t0d, t1d = t0, t1
        subjectPositiond = subjectPosition

    plt.xlim(t0d, t1d)
    plt.yticks(range(len(lbl) + 1), np.array(lbl))

    count = 0
    flagFirstSubject = True

    for subject in all_project_subjects:
        if subject not in obs:
            continue

        if not flagFirstSubject:
            if excludeBehaviorsWithoutEvents:
                count += 1
            ax.axhline(y=(count-1), linewidth=1, color="black")
            ax.hlines(np.array([count]), np.array([0]), np.array([0]), lw=LINE_WIDTH, color=col)
        else:
            flagFirstSubject = False

        ax.text(subjectPositiond, count - 0.5, subject)

        behaviors = obs[subject]

        x1, x2, y, col, pointsx, pointsy, guide = [], [], [], [], [], [], []
        col_count = 0

        for bm_json in all_behaviors:
            if bm_json in obs[subject]:
                if obs[subject][bm_json]:
                    for t1, t2 in obs[subject][bm_json]:
                        if t1 == t2:
                            pointsx.append(t1)
                            pointsy.append(count)
                            ax.axhline(y=count, linewidth=1, color="lightgray", zorder=-1)
                        else:
                            x1.append(t1)
                            x2.append(t2)
                            y.append(count)

                            col.append(utilities.behavior_color(plot_colors, all_project_behaviors.index(json.loads(bm_json)[0])))
                            ax.axhline(y=count, linewidth=1, color="lightgray", zorder=-1)
                    count += 1
                else:
                    x1.append(0)
                    x2.append(0)
                    y.append(count)
                    col.append("white")
                    ax.axhline(y=count, linewidth=1, color="lightgray", zorder=-1)
                    count += 1

            else:
                if not excludeBehaviorsWithoutEvents:
                    x1.append(0)
                    x2.append(0)
                    y.append(count)
                    col.append("white")
                    ax.axhline(y=count, linewidth=1, color="lightgray", zorder=-1)
                    count += 1

            col_count += 1

        if time_format == HHMMSS:
            ax.hlines(np.array(y), np.array([datetime.datetime(1970, 1, 1, int(p / 3600),
                                                               int((p - int(p / 3600) * 3600) / 60),
                                                               int(p % 60), round(round(p % 1, 3) * 1e6))
                                            for p in x1]),
            np.array([datetime.datetime(1970, 1, 1, int(p / 3600), int((p - int(p / 3600) * 3600) / 60), int(p % 60), round(round(p % 1, 3) * 1e6)) for p in x2]),
            lw=LINE_WIDTH, color=col)

        if time_format == S:
            ax.hlines(np.array(y), np.array(x1), np.array(x2), lw=LINE_WIDTH, color=col)

        if time_format == HHMMSS:
            ax.plot(np.array([datetime.datetime(1970, 1, 1, int(p / 3600), int((p - int(p / 3600) * 3600)/60), int(p % 60), round(round(p % 1, 3) * 1e6)) for p in pointsx]), pointsy, "r^")

        if time_format == S:
            ax.plot(pointsx, pointsy, "r^")

        #ax.axhline(y=y[-1] + 0.5,linewidth=1, color='black')

    fig.canvas.mpl_connect("draw_event", on_draw)
    plt.show()

    return True



def create_events_plot2(events,
                        all_behaviors,
                        all_subjects,
                        exclude_behaviors_wo_events=True, min_time=-1, max_time=-1, output_file_name="",
                        plot_colors=BEHAVIORS_PLOT_COLORS):
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
        for ylabel in ylabels:
            if ylabel in events[subject]:
                for interval in events[subject][ylabel]:
                    if interval[0] == interval[1]:
                        start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                        end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0] + point_event_duration))
                        bar_color = "black"
                    else:
                        start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[0]))
                        end_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=interval[1]))
                        bar_color = behav_color(json.loads(ylabel)[0])
                    try:
                        axs[ax_idx].barh((i * par1) + par1, end_date - start_date, left=start_date, height=bar_height,
                                         align="center", edgecolor=bar_color, color=bar_color, alpha = 1)
                    except ValueError:
                        return {"error code": 1, "msg": "Invalid color name: <b>{}</b>".format(bar_color)}
            i += 1

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
    events = {'No focal subject': {'["a", "None|None"]': [[47.187, 56.107]]}, 'subj 2': {'["p"]': [[10.62, 10.62], [11.3, 11.3], [12.044, 12.044], [13.228, 13.228]], '["s"]': [[31.852, 37.308]]}, 'subj 1': {'["p"]': [[7.116, 7.116], [8.5, 8.5], [9.42, 9.42]], '["s"]': [[19.476, 44.564]], '["a", "None"]': [[15.787, 24.01]], '["n", "123"]': [[11.459, 11.459]], '["n", "456"]': [[17.611, 17.611]]}}

    create_events_plot2(events, all_behaviors, all_subjects, exclude_behaviors_wo_events=False, min_time=0, max_time=100)
