import sys
import time
import pprint
import pandas as pd

from . import project_functions
from . import config as cfg
from . import utilities as util


def event_val(event, field, obs_type: str = cfg.MEDIA):
    try:
        return event[cfg.PJ_OBS_FIELDS[obs_type][field]]
    except:
        return None


_, _, pj, _ = project_functions.open_project_json(sys.argv[1])

# pprint.pprint(list(pj[cfg.OBSERVATIONS].keys()))

# print()

"""
obs_id = "images NO TIME"
pprint.pprint(pj[cfg.OBSERVATIONS][obs_id])
"""

state_events_list = util.state_behavior_codes(pj[cfg.ETHOGRAM])

df_def = {
    "observation id": pd.Series(dtype="str"),
    "observation type": pd.Series(dtype="str"),
    "observation description": pd.Series(dtype="str"),
    "subject": pd.Series(dtype="str"),
    "behavior": pd.Series(dtype="str"),
    "modifier": pd.Series(dtype="str"),
    "start": pd.Series(dtype="float"),
    "stop": pd.Series(dtype="float"),
    "duration": pd.Series(dtype="float"),
}
df = pd.DataFrame(df_def)
l = []
# print(df.info)

for obs_id in pj[cfg.OBSERVATIONS]:
    # print(obs_id)
    obs_type = pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]
    obs_descr = pj[cfg.OBSERVATIONS][obs_id][cfg.DESCRIPTION]
    mem_idx = []
    for idx, event in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]):
        if idx in mem_idx:
            continue
        start = event_val(event, cfg.TIME)
        subject = event_val(event, cfg.SUBJECT)
        behavior = event_val(event, cfg.BEHAVIOR_CODE)
        modifier = event_val(event, cfg.MODIFIER)
        if behavior in state_events_list:
            stop = None
            for idx2, event2 in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS][idx + 1 :], start=idx + 1):
                subject2 = event_val(event2, cfg.SUBJECT)
                behavior2 = event_val(event2, cfg.BEHAVIOR_CODE)
                modifier2 = event_val(event2, cfg.MODIFIER)
                if subject == subject2 and behavior == behavior2 and modifier == modifier2:
                    stop = event_val(event2, cfg.TIME)
                    mem_idx.append(idx2)
                    l.append([obs_id, obs_type, obs_descr, subject, behavior, modifier, start, stop, stop - start])
                    break
            if stop is None:
                print(obs_id, " not paired")
                # print(pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])
                # print(f"{l=}")
                # print(f"{mem_idx=}")

                sys.exit()
        else:
            l.append([obs_id, obs_type, obs_descr, subject, behavior, modifier, start, start, 0])

# print(pd.DataFrame(l))
df = pd.concat(
    [
        df,
        pd.DataFrame(
            l,
            columns=[
                "observation id",
                "observation type",
                "observation description",
                "subject",
                "behavior",
                "modifier",
                "start",
                "stop",
                "duration",
            ],
        ),
    ]
)
del l
print("=" * 30)
print("describe")
print(df.describe())
print("=" * 30)

# print(f'{df["subject"].value_counts()=}')
# print(f'{df["subject"].nunique()=}')

pd.set_option("display.max_rows", None, "display.max_columns", None)

print("=" * 30)
print("mean")
r = df.groupby(["subject", "behavior"])["duration"].mean()
print(r)
print("=" * 30)


r = df.groupby(["observation id", "subject", "behavior"])
print(r["start"])


"""
# replace value (for selecting a time interval)
t1 = time.time()
df.loc[df["stop"] > 10, "stop"] = 10
print(time.time() - t1)
print(df)
"""


"""
t1 = 1
t2 = 2
print(df.query(f"`start` <= {t1} & `stop` >= {t2} & `duration` != 0"))
"""
