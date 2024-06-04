"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard


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

import bisect
import logging
from decimal import Decimal as dec
import re
import pathlib as pl

from . import config as cfg
from . import dialog
from . import utilities as util
from . import select_modifiers
from . import event_operations


def write_event(self, event: dict, mem_time: dec) -> int:
    """
    add event from pressed key to observation
    offset is added to event time
    ask for modifiers if configured
    load events in tableview
    scroll to active event

    Args:
        event (dict): event parameters
        memTime (Decimal): time

    """

    logging.debug(f"write event - event: {event}  memtime: {mem_time}")

    if event is None:
        return 1

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:
        # live observation finished (end of time interval reached)
        if not self.liveObservationStarted and mem_time.is_nan():
            _ = dialog.MessageDialog(
                cfg.programName,
                (
                    "The live observation is finished.<br>"
                    "The observation interval is "
                    f"{self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[0]} - "
                    f"{self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]}"
                ),
                (cfg.OK,),
            )
            return 1

        if mem_time < self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[0]:
            _ = dialog.MessageDialog(
                cfg.programName,
                (
                    "The live observation has not began.<br>"
                    "The observation interval is "
                    f"{self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[0]} - "
                    f"{self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]}"
                ),
                (cfg.OK,),
            )
            return 1

    editing_event = "row" in event

    # add time offset if not from editing
    if not editing_event:
        # add offset
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
            mem_time += dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET]).quantize(dec(".001"))

        # add media creation time
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA):
            if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.MEDIA_CREATION_DATE_AS_OFFSET, False):
                media_file_name = self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"]
                mem_time += dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.MEDIA_CREATION_TIME][media_file_name])

    # check if time > 2**31 - 1 (2147483647)
    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.VIEWER_MEDIA, cfg.LIVE, cfg.VIEWER_LIVE):
        if (mem_time < -2147483647) or (mem_time > 2147483647):
            _ = dialog.MessageDialog(
                cfg.programName,
                ("The timestamp must be between -2147483647 and 2147483647.<br>" f"The current timestamp is {mem_time}"),
                (cfg.OK,),
            )
            return 1

    # remove key code from modifiers
    subject = event.get(cfg.SUBJECT, self.currentSubject)
    comment = event.get(cfg.COMMENT, "")

    if self.playerType in (cfg.IMAGES, cfg.VIEWER_IMAGES):
        image_idx = event.get(cfg.IMAGE_INDEX, "")
        image_path = event.get(cfg.IMAGE_PATH, "")
        # check if pictures dir is relative
        if str(pl.Path(image_path).parent) not in self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.DIRECTORIES_LIST, []):
            image_path = str(pl.Path(image_path).relative_to(pl.Path(self.projectFileName).parent))

    if self.playerType in (cfg.MEDIA, cfg.VIEWER_MEDIA):
        frame_idx = event.get(cfg.FRAME_INDEX, cfg.NA)

    # check if a same event is already in events list (time, subject, code)

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
        # adding event
        if (not editing_event) and self.checkSameEvent(
            self.observationId,
            mem_time,
            subject,
            event[cfg.BEHAVIOR_CODE],
        ):
            _ = dialog.MessageDialog(cfg.programName, "The same event already exists (same time, behavior code and subject).", (cfg.OK,))
            return 1

        # modifying event and time was changed
        if editing_event and mem_time != self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]][0]:
            if self.checkSameEvent(
                self.observationId,
                mem_time,
                subject,
                event[cfg.BEHAVIOR_CODE],
            ):
                _ = dialog.MessageDialog(
                    cfg.programName,
                    "The same event already exists (same time, behavior code and subject).",
                    [cfg.OK],
                )
                return 1

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
        # adding event
        if (not editing_event) and self.checkSameEvent(
            self.observationId,
            image_idx,
            subject,
            event[cfg.BEHAVIOR_CODE],
        ):
            _ = dialog.MessageDialog(
                cfg.programName,
                "The same event already exists (same image index, behavior code and subject).",
                [cfg.OK],
            )
            return 1

        # modifying event and time was changed
        if (
            editing_event
            and image_idx
            != self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]][cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_INDEX]]
        ):
            if self.checkSameEvent(
                self.observationId,
                image_idx,
                subject,
                event[cfg.BEHAVIOR_CODE],
            ):
                _ = dialog.MessageDialog(
                    cfg.programName,
                    "The same event already exists (same image index, behavior code and subject).",
                    (cfg.OK,),
                )
                return 1

    # extract State events
    state_behaviors_codes = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])

    # index of current subject
    # subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.LIVE, cfg.MEDIA):
        position = mem_time
    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
        position = dec(image_idx)  # decimal to pass to util.get_current_states_modifiers_by_subject

    current_states: dict = util.get_current_states_modifiers_by_subject(
        state_behaviors_codes,
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
        dict(self.pj[cfg.SUBJECTS], **{"": {"name": ""}}),
        position,
        include_modifiers=False,
    )

    # check if ask modifiers at stop is enabled
    flag_ask_at_stop = False
    if event["type"] == cfg.STATE_EVENT:
        for idx in event[cfg.MODIFIERS]:
            if event[cfg.MODIFIERS][idx].get("ask at stop", False):
                flag_ask_at_stop = True
                break

    flag_ask_modifier = False
    if flag_ask_at_stop:
        # TODO: check if new event is a STOP one

        idx_subject: str = ""
        for idx in current_states:
            if idx in self.pj[cfg.SUBJECTS] and self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] == self.currentSubject:
                idx_subject = idx
                break

        if event[cfg.BEHAVIOR_CODE] in current_states[idx_subject]:
            flag_ask_modifier = True
    else:
        flag_ask_modifier = True

    if flag_ask_modifier:
        if "from map" in event:  # modifiers only for behaviors without coding map
            modifier_str = event["from map"]
        else:
            # check if event has modifiers
            modifier_str: str = ""

            if event[cfg.MODIFIERS]:
                selected_modifiers: dict = {}
                modifiers_external_data: dict = {}
                # check if modifiers are from external data
                for idx in event[cfg.MODIFIERS]:
                    if event[cfg.MODIFIERS][idx]["type"] == cfg.EXTERNAL_DATA_MODIFIER:
                        if editing_event:
                            original_modifiers_list = event.get("original_modifiers", "").split("|")
                            modifiers_external_data[idx] = dict(event[cfg.MODIFIERS][idx])
                            modifiers_external_data[idx]["selected"] = original_modifiers_list[int(idx)]

                        else:  # no edit
                            for idx2 in self.plot_data:
                                if self.plot_data[idx2].y_label.upper() == event[cfg.MODIFIERS][idx]["name"].upper():
                                    modifiers_external_data[idx] = dict(event[cfg.MODIFIERS][idx])
                                    modifiers_external_data[idx]["selected"] = self.plot_data[idx2].lb_value.text()

                # check if modifiers are in single, multiple or numeric
                if [x for x in event[cfg.MODIFIERS] if event[cfg.MODIFIERS][x]["type"] != cfg.EXTERNAL_DATA_MODIFIER]:
                    # pause media
                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA):
                        if self.playerType == cfg.MEDIA:
                            if self.dw_player[0].player.pause:
                                memState = cfg.PAUSED
                            elif self.dw_player[0].player.time_pos is not None:
                                memState = cfg.PLAYING
                            else:
                                memState = cfg.STOPPED
                            if memState == cfg.PLAYING:
                                self.pause_video()

                    # check if editing (original_modifiers key)
                    currentModifiers = event.get("original_modifiers", "")

                    # print(f"{event=}")

                    modifiers_selector = select_modifiers.ModifiersList(
                        event[cfg.BEHAVIOR_CODE], eval(str(event[cfg.MODIFIERS])), currentModifiers
                    )

                    r = modifiers_selector.exec_()
                    if r:
                        selected_modifiers = modifiers_selector.get_modifiers()

                    # restart media
                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                        if self.playerType == cfg.MEDIA:
                            if memState == cfg.PLAYING:
                                self.play_video()
                    if not r:  # cancel button pressed
                        return

                all_modifiers = {**selected_modifiers, **modifiers_external_data}

                modifier_str: str = ""
                for idx in util.sorted_keys(all_modifiers):
                    if modifier_str:
                        modifier_str += "|"
                    if all_modifiers[idx]["type"] in (cfg.SINGLE_SELECTION, cfg.MULTI_SELECTION):
                        modifier_str += ",".join(all_modifiers[idx].get("selected", ""))
                    if all_modifiers[idx]["type"] in (cfg.NUMERIC_MODIFIER, cfg.EXTERNAL_DATA_MODIFIER):
                        modifier_str += all_modifiers[idx].get("selected", "NA")

        modifier_str = re.sub(r" \(.*\)", "", modifier_str)
    else:  # do not ask modifier
        modifier_str = ""

    # update current state
    # TODO: verify event["subject"] / self.currentSubject

    # print(f"{current_states=}")

    # logging.debug(f"self.currentSubject {self.currentSubject}")
    # logging.debug(f"current_states {current_states}")

    # fill the undo list
    event_operations.fill_events_undo_list(self, "Undo last event edition" if editing_event else "Undo last event insertion")

    logging.debug("save list of events for undo operation")

    if not editing_event:
        if self.currentSubject:
            csj: list = []  # list of current state for the current subject
            for idx in current_states:
                if idx in self.pj[cfg.SUBJECTS] and self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] == self.currentSubject:
                    csj = current_states[idx]
                    break

        else:  # no focal subject
            try:
                csj = current_states[""]
            except Exception:
                csj = []

        logging.debug(f"csj {csj}")

        # print(f"{csj=}")

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.LIVE, cfg.MEDIA):
            check_index = cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE]][cfg.TIME]
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            check_index = cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_INDEX]

        cm: dict = {}  # modifiers for current behaviors
        for cs in csj:
            for ev in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]:
                if ev[check_index] > position:
                    break

                if ev[cfg.EVENT_SUBJECT_FIELD_IDX] == self.currentSubject:
                    if ev[cfg.EVENT_BEHAVIOR_FIELD_IDX] == cs:
                        cm[cs] = ev[cfg.EVENT_MODIFIER_FIELD_IDX]

        # print(f"{cm=}")

        if flag_ask_at_stop:
            # set modifier to START behavior
            if event[cfg.BEHAVIOR_CODE] in csj:
                mem_idx = -1
                for idx, e in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
                    # print(f"{e=}")
                    if e[0] >= mem_time:
                        break
                    # same behavior, same subject and modifier(s) not set
                    if e[2] == event[cfg.BEHAVIOR_CODE] and e[1] == self.currentSubject and e[3] == "":
                        mem_idx = idx
                if mem_idx != -1:
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][mem_idx][3] = modifier_str
                    csj.remove(event[cfg.BEHAVIOR_CODE])

        for cs in csj:
            # close state if same state without modifier
            if (
                self.close_the_same_current_event
                and (event[cfg.BEHAVIOR_CODE] == cs)
                and modifier_str.replace("None", "").replace("|", "") == ""
            ):
                modifier_str = cm[cs]
                continue

            if (event[cfg.EXCLUDED] and cs in event[cfg.EXCLUDED].split(",")) or (
                event[cfg.BEHAVIOR_CODE] == cs and cm[cs] != modifier_str
            ):
                # check if behavior to stop is a 'ask modifier at stop'
                behavior_to_stop = [
                    self.pj[cfg.ETHOGRAM][x]
                    for x in self.pj[cfg.ETHOGRAM]
                    if self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] == cs and self.pj[cfg.ETHOGRAM][x]["type"] == cfg.STATE_EVENT
                ]
                if behavior_to_stop:
                    behavior_to_stop = behavior_to_stop[0]

                    flag_behavior_ask_at_stop = False
                    for idx in behavior_to_stop[cfg.MODIFIERS]:
                        if behavior_to_stop[cfg.MODIFIERS][idx].get("ask at stop", False):
                            flag_behavior_ask_at_stop = True
                            break
                    if flag_behavior_ask_at_stop:
                        modifiers_selector = select_modifiers.ModifiersList(
                            behavior_to_stop[cfg.BEHAVIOR_CODE],
                            eval(str(behavior_to_stop[cfg.MODIFIERS])),
                            currentModifier="",
                        )

                        r = modifiers_selector.exec_()
                        if r:
                            selected_modifiers = modifiers_selector.get_modifiers()
                            # print(f"{selected_modifiers=}")

                            behavior_to_stop_modifier_str: str = ""
                            for idx in util.sorted_keys(selected_modifiers):
                                if behavior_to_stop_modifier_str:
                                    behavior_to_stop_modifier_str += "|"
                                if selected_modifiers[idx]["type"] in (cfg.SINGLE_SELECTION, cfg.MULTI_SELECTION):
                                    behavior_to_stop_modifier_str += ",".join(selected_modifiers[idx].get("selected", ""))
                                if selected_modifiers[idx]["type"] in (cfg.NUMERIC_MODIFIER, cfg.EXTERNAL_DATA_MODIFIER):
                                    behavior_to_stop_modifier_str += selected_modifiers[idx].get("selected", "NA")

                            # set the start modifier
                            mem_idx = -1
                            for idx, e in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
                                if e[0] >= mem_time - dec("0.001"):
                                    break
                                # same behavior, same subject and modifier(s) not set
                                if e[2] == behavior_to_stop[cfg.BEHAVIOR_CODE] and e[1] == self.currentSubject and e[3] == "":
                                    mem_idx = idx
                            if mem_idx != -1:
                                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][mem_idx][3] = behavior_to_stop_modifier_str

                    else:
                        behavior_to_stop_modifier_str = cm[cs]

                # add excluded state event to observations (= STOP them)
                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.LIVE):
                    bisect.insort(
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
                        [mem_time - dec("0.001"), self.currentSubject, cs, behavior_to_stop_modifier_str, ""],
                    )

                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA):
                    bisect.insort(
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
                        [mem_time - dec("0.001"), self.currentSubject, cs, behavior_to_stop_modifier_str, "", cfg.NA],
                    )

                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.IMAGES):
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].append(
                        [mem_time, self.currentSubject, cs, behavior_to_stop_modifier_str, "", image_idx, image_path]
                    )

                    # order by image index ASC
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort(
                        key=lambda x: x[cfg.PJ_OBS_FIELDS[self.playerType][cfg.IMAGE_INDEX]]
                    )

    # add event to pj
    if editing_event:  # modifying event
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]] = [
                mem_time,
                subject,
                event[cfg.BEHAVIOR_CODE],
                modifier_str,
                comment,
                frame_idx,
            ]
            # order by image index ASC
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()

        elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]] = [
                mem_time,
                subject,
                event[cfg.BEHAVIOR_CODE],
                modifier_str,
                comment,
            ]
            # order by image index ASC
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()

        elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]] = [
                mem_time,
                subject,
                event[cfg.BEHAVIOR_CODE],
                modifier_str,
                comment,
                image_idx,
                image_path,
            ]
            # order by image index ASC
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort(
                key=lambda x: x[cfg.PJ_OBS_FIELDS[self.playerType][cfg.IMAGE_INDEX]]
            )

    else:  # add event
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            bisect.insort(
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
                [mem_time, subject, event[cfg.BEHAVIOR_CODE], modifier_str, comment, frame_idx],
            )
        elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:
            bisect.insort(
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
                [mem_time, subject, event[cfg.BEHAVIOR_CODE], modifier_str, comment],
            )

        elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].append(
                [mem_time, subject, event[cfg.BEHAVIOR_CODE], modifier_str, comment, image_idx, image_path]
            )
            # order by image index ASC
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort(
                key=lambda x: x[cfg.PJ_OBS_FIELDS[self.playerType][cfg.IMAGE_INDEX]]
            )

    # reload all events in tw
    self.load_tw_events(self.observationId)

    self.project_changed()

    self.get_events_current_row()

    # index of current subject selected by observer
    subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

    self.currentStates = util.get_current_states_modifiers_by_subject(
        self.state_behaviors_codes,
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
        dict(self.pj[cfg.SUBJECTS], **{"": {"name": ""}}),
        self.getLaps(),
        include_modifiers=True,
    )

    self.lbCurrentStates.setText(f"Observed behaviors: {', '.join(self.currentStates[subject_idx])}")
    # show current states in subjects table
    self.show_current_states_in_subjects_table()

    return 0
