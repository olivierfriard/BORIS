            
def loadEventsInDB(self, selectedSubjects, selectedObservations, selectedBehaviors):
    
    cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

    for subject in plot_parameters["selected subjects"]:

        for behavior in plot_parameters["selected behaviors"]:

            cursor.execute("SELECT occurence, modifiers, comment FROM events WHERE observation = ? AND subject = ? AND code = ? ORDER by occurence", (obsId, subject, behavior))
            rows = list(cursor.fetchall())

            if STATE in self.eventType(behavior).upper() and len(rows) % 2:  # unpaired events
                flagUnpairedEventFound = True
                continue

            for idx, row in enumerate(rows):

                if self.pj[OBSERVATIONS][obsId]["type"] in [MEDIA]:

                    mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if row["occurence"] >= sum(duration1[0:idx1])][-1]
                    mediaFileString = self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx]
                    fpsString = self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx]]

                if self.pj[OBSERVATIONS][obsId]["type"] in [LIVE]:
                    mediaFileString = "LIVE"
                    fpsString = "NA"

                if POINT in self.eventType(behavior).upper():

                    if outputFormat == "sql":
                        out += template.format(observation=obsId,
                                            date=self.pj[OBSERVATIONS][obsId]["date"].replace("T", " "),
                                            media_file=mediaFileString,
                                            total_length=total_length,
                                            fps=fpsString,
                                            subject=subject,
                                            behavior=behavior,
                                            modifiers=row["modifiers"].strip(),
                                            event_type=POINT,
                                            start="{0:.3f}".format(row["occurence"]),
                                            stop=0,
                                            comment_start=row["comment"],
                                            comment_stop="")
                    else:
                        row_data = []
                        row_data.extend([obsId,
                                    self.pj[OBSERVATIONS][obsId]["date"].replace("T", " "),
                                    mediaFileString,
                                    total_length,
                                    fpsString])

                        # independent variables
                        if "independent_variables" in self.pj:
                            for idx_var in sorted_keys(self.pj["independent_variables"]):
                                if self.pj["independent_variables"][idx_var]["label"] in self.pj[OBSERVATIONS][obsId]["independent_variables"]:
                                   row_data.append(self.pj[OBSERVATIONS][obsId]["independent_variables"][self.pj["independent_variables"][idx_var]["label"]])
                                else:
                                    row_data.append("")

                        row_data.extend([subject,
                                    behavior,
                                    row["modifiers"].strip(),
                                    POINT,
                                    "{0:.3f}".format(row["occurence"]), # start
                                    "NA", # stop
                                    "NA", # duration
                                    row["comment"],
                                    ""
                                    ])
                        data.append(row_data)


                if STATE in self.eventType(behavior).upper():
                    if idx % 2 == 0:
                        if outputFormat == "sql":
                            out += template.format(observation=obsId,
                                                date=self.pj[OBSERVATIONS][obsId]["date"].replace("T", " "),
                                                media_file=mediaFileString,
                                                total_length=total_length,
                                                fps=fpsString,
                                                subject=subject,
                                                behavior=behavior,
                                                modifiers=row["modifiers"].strip(),
                                                event_type=STATE,
                                                start="{0:.3f}".format(row["occurence"]),
                                                stop="{0:.3f}".format(rows[idx + 1]["occurence"]),
                                                comment_start=row["comment"],
                                                comment_stop=rows[idx + 1]["comment"])

                        else:
                            row_data = []

                            row_data.extend([obsId,
                                    self.pj[OBSERVATIONS][obsId]["date"].replace("T", " "),
                                    mediaFileString,
                                    total_length,
                                    fpsString])

                            # independent variables
                            if "independent_variables" in self.pj:
                                for idx_var in sorted_keys(self.pj["independent_variables"]):
                                    if self.pj["independent_variables"][idx_var]["label"] in self.pj[OBSERVATIONS][obsId]["independent_variables"]:
                                       row_data.append(self.pj[OBSERVATIONS][obsId]["independent_variables"][self.pj["independent_variables"][idx_var]["label"]])
                                    else:
                                        row_data.append("")

                            row_data.extend([subject,
                                    behavior,
                                    row["modifiers"].strip(),
                                    STATE,
                                    "{0:.3f}".format(row["occurence"]),
                                    "{0:.3f}".format(rows[idx + 1]["occurence"]),
                                    "{0:.3f}".format(rows[idx + 1]["occurence"] - row["occurence"]),
                                    row["comment"],
                                    rows[idx + 1]["comment"]
                                    ])

                            data.append(row_data)
