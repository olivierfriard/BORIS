import sqlite3
from config import *


def load_events_in_db(pj, selectedSubjects, selectedObservations, selectedBehaviors):
    """
    populate an memory sqlite database with events from selectedObservations, selectedSubjects and selectedBehaviors
    
    Args:
        selectedObservations (list):
        selectedSubjects (list):
        selectedBehaviors (list):
        
    Returns:
        database cursor:

    """
    
    # selected behaviors defined as state event
    state_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]
    
    db = sqlite3.connect(":memory:")

    '''
    if os.path.isfile("/tmp/boris_debug.sqlite"):
        os.system("rm /tmp/boris_debug.sqlite")
    db = sqlite3.connect("/tmp/boris_debug.sqlite")
    '''

    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE events (observation TEXT,
                                           subject TEXT,
                                           code TEXT,
                                           type TEXT,
                                           modifiers TEXT,
                                           occurence FLOAT,
                                           comment TEXT)""")

    for subject_to_analyze in selectedSubjects:

        for obsId in selectedObservations:

            for event in pj[OBSERVATIONS][obsId][EVENTS]:

                if event[EVENT_BEHAVIOR_FIELD_IDX] in selectedBehaviors:

                    # extract time, code, modifier and comment (time:0, subject:1, code:2, modifier:3, comment:4)
                    if ((subject_to_analyze == NO_FOCAL_SUBJECT and event[EVENT_SUBJECT_FIELD_IDX] == "") or
                            (event[EVENT_SUBJECT_FIELD_IDX] == subject_to_analyze)):

                        r = cursor.execute("""INSERT INTO events
                                               (observation, subject, code, type, modifiers, occurence, comment)
                                                VALUES (?,?,?,?,?,?,?)""",
                        (obsId,
                         NO_FOCAL_SUBJECT if event[EVENT_SUBJECT_FIELD_IDX] == "" else event[EVENT_SUBJECT_FIELD_IDX],
                         event[EVENT_BEHAVIOR_FIELD_IDX],
                         STATE if event[EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes else POINT,
                         event[EVENT_MODIFIER_FIELD_IDX], 
                         str(event[EVENT_TIME_FIELD_IDX]),
                         event[EVENT_COMMENT_FIELD_IDX]))

    db.commit()
    return cursor



def load_events_start_stop_in_db(pj, selectedSubjects, selectedObservations, selectedBehaviors):
    
    if not selectedObservations:
        selectedObservations = sorted([x for x in pj[OBSERVATIONS]])

    if not selectedSubjects:
        selectedSubjects = sorted([pj[SUBJECTS][x]["name"] for x in pj[SUBJECTS]] + [NO_FOCAL_SUBJECT])

    if not selectedBehaviors:
        selectedBehaviors = sorted([pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]])



    # selected behaviors defined as state event
    state_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]

    
    out = "CREATE TABLE events (id INTEGER PRIMARY KEY ASC, observation TEXT, date DATE, media_file TEXT, subject TEXT, behavior TEXT, modifiers TEXT, event_type TEXT, start FLOAT, stop FLOAT, comment_start TEXT, comment_stop TEXT);" + "\n"
    out += "BEGIN TRANSACTION;\n"
    template = """INSERT INTO events (observation, date, media_file, subject, behavior, modifiers, event_type, start, stop, comment_start, comment_stop) VALUES ("{observation}","{date}", "{media_file}", "{subject}", "{behavior}","{modifiers}","{event_type}",{start},{stop},"{comment_start}","{comment_stop}");\n"""

    cursor1 = load_events_in_db(pj, selectedSubjects, selectedObservations, selectedBehaviors)
    
    #db = sqlite3.connect(":memory:")
    db = sqlite3.connect("/tmp/1.sqlite")
    db.row_factory = sqlite3.Row
    cursor2 = db.cursor()
    cursor2.execute("""CREATE TABLE events (id INTEGER PRIMARY KEY ASC,
                               observation TEXT,
                               subject TEXT,
                               behavior TEXT,
                               type TEXT,
                               modifiers TEXT,
                               start FLOAT,
                               stop FLOAT,
                               comment TEXT)""")
                               

    for obsId in selectedObservations:
    
        for subject in selectedSubjects:
    
            for behavior in selectedBehaviors:
    
                cursor1.execute("SELECT occurence, modifiers, comment FROM events WHERE observation = ? AND subject = ? AND code = ? ORDER by occurence", (obsId, subject, behavior))
                rows = list(cursor1.fetchall())
    
                for idx, row in enumerate(rows):
    
                    if behavior in point_behaviors_codes:
                        
                        cursor2.execute("INSERT INTO events (observation, subject, behavior, type, modifiers, start, stop) VALUES (?,?,?,?,?,?,?)",
                                                            (obsId, subject, behavior, POINT, row["modifiers"].strip(), row["occurence"], row["occurence"]))
    
    
                    if behavior in state_behaviors_codes:
                        if idx % 2 == 0:
                            
                            cursor2.execute("INSERT INTO events (observation, subject, behavior, type, modifiers, start, stop) VALUES (?,?,?,?,?,?,?)",
                                                            (obsId, subject, behavior, STATE, row["modifiers"].strip(), row["occurence"], rows[idx + 1]["occurence"]))

    db.commit()
    return cursor2


if __name__ == '__main__':


    false = False
    true = True

    p = {
 "time_format":"hh:mm:ss",
 "project_date":"2017-09-20T16:45:11",
 "project_name":"",
 "project_description":"",
 "project_format_version":"4.0",
 "subjects_conf":{
  "0":{
   "key":"2",
   "name":"subj 2",
   "description":""
  },
  "1":{
   "key":"1",
   "name":"subj 1",
   "description":""
  }
 },
 "behaviors_conf":{
  "0":{
   "type":"Point event",
   "key":"P",
   "code":"p",
   "description":"",
   "category":"",
   "modifiers":"",
   "excluded":"",
   "coding map":""
  },
  "1":{
   "type":"State event",
   "key":"S",
   "code":"s",
   "description":"",
   "category":"",
   "modifiers":"",
   "excluded":"",
   "coding map":""
  },
  "2":{
   "type":"State event",
   "key":"A",
   "code":"a",
   "description":"",
   "category":"",
   "modifiers":{
    "0":{
     "name":"set1",
     "type":1,
     "values":[
      "aaa (A)",
      "bbb (B)",
      "ccc (C)"
     ]
    },
    "1":{
     "name":"set2",
     "type":0,
     "values":[
      "ddd (D)",
      "eee (E)"
     ]
    }
   },
   "excluded":"",
   "coding map":""
  },
  "3":{
   "type":"Point event",
   "key":"N",
   "code":"n",
   "description":"",
   "category":"",
   "modifiers":{
    "0":{
     "name":"num1",
     "type":2,
     "values":[]
    }
   },
   "excluded":"",
   "coding map":""
  },
  "4":{
   "type":"Point event",
   "key":"X",
   "code":"x",
   "description":"",
   "category":"",
   "modifiers":"",
   "excluded":"",
   "coding map":""
  },
  "5":{
   "type":"State event",
   "key":"Y",
   "code":"y",
   "description":"",
   "category":"",
   "modifiers":"",
   "excluded":"",
   "coding map":""
  }
 },
 "observations":{
  "live2":{
   "file":[],
   "type":"LIVE",
   "date":"2017-09-20T16:59:13",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     4.206,
     "",
     "p",
     "",
     ""
    ],
    [
     5.806,
     "",
     "p",
     "",
     ""
    ],
    [
     6.342,
     "",
     "p",
     "",
     ""
    ],
    [
     7.374,
     "",
     "s",
     "",
     ""
    ],
    [
     10.71,
     "",
     "s",
     "",
     ""
    ],
    [
     12.038,
     "",
     "p",
     "",
     ""
    ],
    [
     12.718,
     "",
     "p",
     "",
     ""
    ],
    [
     13.142,
     "",
     "p",
     "",
     ""
    ]
   ],
   "independent_variables":{},
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "live with subjects":{
   "file":[],
   "type":"LIVE",
   "date":"2017-09-22T18:12:46",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     7.116,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     8.5,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     9.42,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     10.62,
     "subj 2",
     "p",
     "",
     ""
    ],
    [
     11.3,
     "subj 2",
     "p",
     "",
     ""
    ],
    [
     11.459,
     "subj 1",
     "n",
     "123",
     ""
    ],
    [
     12.044,
     "subj 2",
     "p",
     "",
     ""
    ],
    [
     13.228,
     "subj 2",
     "p",
     "",
     ""
    ],
    [
     15.787,
     "subj 1",
     "a",
     "None|None",
     ""
    ],
    [
     17.611,
     "subj 1",
     "n",
     "456",
     ""
    ],
    [
     19.476,
     "subj 1",
     "s",
     "",
     ""
    ],
    [
     24.01,
     "subj 1",
     "a",
     "None|None",
     ""
    ],
    [
     31.852,
     "subj 2",
     "s",
     "",
     ""
    ],
    [
     37.308,
     "subj 2",
     "s",
     "",
     ""
    ],
    [
     44.564,
     "subj 1",
     "s",
     "",
     ""
    ],
    [
     47.187,
     "",
     "a",
     "None|None",
     ""
    ],
    [
     56.107,
     "",
     "a",
     "None|None",
     ""
    ],
    [
     59.171,
     "",
     "a",
     "aaa,bbb|ddd",
     ""
    ],
    [
     69.091,
     "",
     "a",
     "aaa,bbb|ddd",
     ""
    ]
   ],
   "independent_variables":{},
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "live no subject modifiers":{
   "file":[],
   "type":"LIVE",
   "date":"2017-09-20T17:03:23",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     1.533,
     "",
     "a",
     "None|None",
     ""
    ],
    [
     2.964,
     "",
     "n",
     "123",
     ""
    ],
    [
     7.539,
     "",
     "a",
     "aaa,ccc|eee",
     ""
    ],
    [
     9.813,
     "",
     "a",
     "None|None",
     ""
    ],
    [
     16.491,
     "",
     "a",
     "aaa,ccc|eee",
     ""
    ],
    [
     20.349,
     "",
     "a",
     "bbb|ddd",
     ""
    ],
    [
     58.74,
     "",
     "a",
     "bbb|ddd",
     ""
    ]
   ],
   "independent_variables":{},
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "live no subject numeric modifier":{
   "file":[],
   "type":"LIVE",
   "date":"2017-09-21T15:44:43",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     0.844,
     "",
     "n",
     "100",
     ""
    ],
    [
     2.203,
     "",
     "n",
     "200",
     ""
    ],
    [
     4.324,
     "",
     "n",
     "100",
     ""
    ],
    [
     5.978,
     "",
     "n",
     "200",
     ""
    ],
    [
     6.58,
     "",
     "n",
     "100",
     ""
    ],
    [
     9.034,
     "",
     "n",
     "300",
     ""
    ],
    [
     12.178,
     "",
     "n",
     "200",
     ""
    ]
   ],
   "independent_variables":{},
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "aaa * / [123]":{
   "file":[],
   "type":"LIVE",
   "date":"2017-10-10T11:45:49",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     2.877,
     "",
     "p",
     "",
     ""
    ],
    [
     3.429,
     "",
     "p",
     "",
     ""
    ],
    [
     3.933,
     "",
     "p",
     "",
     ""
    ],
    [
     6.397,
     "",
     "s",
     "",
     ""
    ],
    [
     8.309,
     "",
     "s",
     "",
     ""
    ],
    [
     9.413,
     "",
     "s",
     "",
     ""
    ],
    [
     10.973,
     "",
     "s",
     "",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"1",
    "v2":"abc"
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "live4":{
   "file":[],
   "type":"LIVE",
   "date":"2017-10-20T11:06:14",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     1.16,
     "",
     "s",
     "",
     ""
    ],
    [
     6.024,
     "",
     "s",
     "",
     ""
    ],
    [
     6.744,
     "",
     "s",
     "",
     ""
    ],
    [
     9.04,
     "",
     "s",
     "",
     ""
    ],
    [
     11.576,
     "",
     "s",
     "",
     ""
    ],
    [
     16.928,
     "",
     "s",
     "",
     ""
    ],
    [
     18.64,
     "",
     "s",
     "",
     ""
    ],
    [
     23.016,
     "",
     "s",
     "",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"",
    "v2":"test"
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "video 2 subj no modifiers":{
   "file":{
    "1":[
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi"
    ],
    "2":[]
   },
   "type":"MEDIA",
   "date":"2017-09-25T15:52:13",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     5.675,
     "subj 1",
     "s",
     "",
     ""
    ],
    [
     9.925,
     "subj 1",
     "s",
     "",
     ""
    ],
    [
     14.65,
     "subj 2",
     "s",
     "",
     ""
    ],
    [
     24.75,
     "subj 2",
     "s",
     "",
     ""
    ],
    [
     28.343,
     "",
     "p",
     "",
     ""
    ],
    [
     31.015,
     "",
     "p",
     "",
     ""
    ],
    [
     33.19,
     "",
     "p",
     "",
     ""
    ],
    [
     36.094,
     "",
     "p",
     "",
     ""
    ],
    [
     47.544,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     49.094,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     49.619,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     49.894,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     50.419,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     50.694,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     50.969,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     51.494,
     "subj 1",
     "p",
     "",
     ""
    ],
    [
     51.769,
     "subj 1",
     "p",
     "",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"",
    "v2":""
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "media_info":{
    "length":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":225.64
    },
    "fps":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":25.0
    },
    "hasVideo":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":true
    },
    "hasAudio":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":true
    }
   }
  },
  "video no subj no modifiers":{
   "file":{
    "1":[
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi"
    ],
    "2":[]
   },
   "type":"MEDIA",
   "date":"2017-11-03T14:36:35",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     4.95,
     "",
     "p",
     "",
     ""
    ],
    [
     5.775,
     "",
     "p",
     "",
     ""
    ],
    [
     6.55,
     "",
     "p",
     "",
     ""
    ],
    [
     7.625,
     "",
     "s",
     "",
     ""
    ],
    [
     20.175,
     "",
     "s",
     "",
     ""
    ],
    [
     66.464,
     "",
     "s",
     "",
     ""
    ],
    [
     147.121,
     "",
     "s",
     "",
     ""
    ],
    [
     171.621,
     "",
     "s",
     "",
     ""
    ],
    [
     213.261,
     "",
     "s",
     "",
     ""
    ],
    [
     216.486,
     "",
     "s",
     "",
     ""
    ],
    [
     225.511,
     "",
     "s",
     "",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"",
    "v2":"test"
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "media_info":{
    "length":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":225.64
    },
    "fps":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":25.0
    },
    "hasVideo":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":true
    },
    "hasAudio":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/crop.avi":true
    }
   }
  },
  "live #2 no subj no modif":{
   "file":[],
   "type":"LIVE",
   "date":"2017-11-03T14:45:01",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     1.0,
     "",
     "s",
     "",
     ""
    ],
    [
     10.0,
     "",
     "s",
     "",
     ""
    ],
    [
     20.0,
     "",
     "s",
     "",
     ""
    ],
    [
     31.0,
     "",
     "s",
     "",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"",
    "v2":"test"
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "live #1 no subj no modif":{
   "file":[],
   "type":"LIVE",
   "date":"2017-09-20T16:46:42",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     1.0,
     "",
     "s",
     "",
     ""
    ],
    [
     5.5,
     "",
     "p",
     "",
     ""
    ],
    [
     10.0,
     "",
     "s",
     "",
     ""
    ],
    [
     20.0,
     "",
     "s",
     "",
     ""
    ],
    [
     30.0,
     "",
     "s",
     "",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"123",
    "v2":"abc"
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "live1":{
   "file":[],
   "type":"LIVE",
   "date":"2018-01-23T14:03:38",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     2.27,
     "",
     "s",
     "",
     ""
    ],
    [
     4.878,
     "",
     "s",
     "",
     ""
    ],
    [
     5.998,
     "subj 1",
     "s",
     "",
     ""
    ],
    [
     9.478,
     "subj 1",
     "s",
     "",
     ""
    ],
    [
     10.342,
     "",
     "s",
     "",
     ""
    ],
    [
     14.254,
     "",
     "s",
     "",
     ""
    ],
    [
     18.748,
     "",
     "s",
     "",
     ""
    ],
    [
     22.02,
     "",
     "s",
     "",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"",
    "v2":"test"
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  },
  "live modifiers":{
   "file":[],
   "type":"LIVE",
   "date":"2018-01-23T16:22:01",
   "description":"",
   "time offset":0.0,
   "events":[
    [
     3.743,
     "",
     "s",
     "",
     ""
    ],
    [
     9.719,
     "",
     "s",
     "",
     ""
    ],
    [
     11.135,
     "",
     "a",
     "aaa|None",
     ""
    ],
    [
     22.87,
     "",
     "a",
     "aaa|None",
     ""
    ],
    [
     22.871,
     "",
     "a",
     "None|None",
     ""
    ],
    [
     35.759,
     "",
     "a",
     "None|None",
     ""
    ]
   ],
   "independent_variables":{
    "v1":"",
    "v2":"test"
   },
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "scan_sampling_time":0
  }
 },
 "behavioral_categories":[],
 "independent_variables":{
  "0":{
   "label":"v1",
   "description":"variable #1",
   "type":"numeric",
   "default value":"",
   "possible values":""
  },
  "1":{
   "label":"v2",
   "description":"variable #2",
   "type":"text",
   "default value":"test",
   "possible values":""
  }
 },
 "coding_map":{},
 "behaviors_coding_map":[],
 "converters":{}
}
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
     
    
    load_events_start_stop_in_db(p, [], [], [])
