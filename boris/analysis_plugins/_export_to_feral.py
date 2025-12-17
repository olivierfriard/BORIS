"""
BORIS plugin

Export observations to FERAL (getferal.ai)
"""

import json
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

__version__ = "0.3.1"
__version_date__ = "2025-12-12"
__plugin_name__ = "Export observations to FERAL"
__author__ = "Olivier Friard - University of Torino - Italy"


# ---------------------------
# Dialog: choose behaviors
# ---------------------------
class BehaviorSelectDialog(QDialog):
    """Select which BORIS behavior codes should become FERAL classes.

    Class 0 is reserved for "other". Any behavior not selected is mapped to 0.
    """

    def __init__(self, behavior_codes, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Select behaviors to export (0 is 'other')")
        self.setModal(True)

        main_layout = QVBoxLayout(self)

        info = QLabel(
            "Select behaviors to export.\n"
            "Class 0 is reserved for 'other'.\n"
            "Unselected behaviors are mapped to 0."
        )
        info.setWordWrap(True)
        main_layout.addWidget(info)

        self.list_behaviors = QListWidget()
        self.list_behaviors.setSelectionMode(QListWidget.ExtendedSelection)

        for code in sorted(behavior_codes):
            item = QListWidgetItem(code)
            item.setSelected(True)  # default: select all
            self.list_behaviors.addItem(item)

        main_layout.addWidget(self.list_behaviors)

        buttons_layout = QHBoxLayout()
        btn_all = QPushButton("Select all")
        btn_none = QPushButton("Select none")
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")

        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._select_none)
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        buttons_layout.addWidget(btn_all)
        buttons_layout.addWidget(btn_none)
        buttons_layout.addStretch()
        buttons_layout.addWidget(btn_ok)
        buttons_layout.addWidget(btn_cancel)

        main_layout.addLayout(buttons_layout)

    def _select_all(self):
        for i in range(self.list_behaviors.count()):
            self.list_behaviors.item(i).setSelected(True)

    def _select_none(self):
        for i in range(self.list_behaviors.count()):
            self.list_behaviors.item(i).setSelected(False)

    def selected_codes(self):
        return [it.text() for it in self.list_behaviors.selectedItems()]


# ---------------------------
# Dialog: split videos
# ---------------------------
class CategoryDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Organize the videos in categories")
        self.setModal(True)

        main_layout = QVBoxLayout(self)
        lists_layout = QHBoxLayout()

        self.list_unclassified = self._make_list_widget()
        self.list_train = self._make_list_widget()
        self.list_val = self._make_list_widget()
        self.list_test = self._make_list_widget()
        self.list_inference = self._make_list_widget()

        lists_layout.addLayout(self._make_column("All videos", self.list_unclassified))
        lists_layout.addLayout(self._make_column("train", self.list_train))
        lists_layout.addLayout(self._make_column("val", self.list_val))
        lists_layout.addLayout(self._make_column("test", self.list_test))
        lists_layout.addLayout(self._make_column("inference", self.list_inference))

        main_layout.addLayout(lists_layout)

        buttons_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(btn_ok)
        buttons_layout.addWidget(btn_cancel)
        main_layout.addLayout(buttons_layout)

        for text in items:
            QListWidgetItem(text, self.list_unclassified)

    @staticmethod
    def _make_column(title, widget):
        col = QVBoxLayout()
        col.addWidget(QLabel(title))
        col.addWidget(widget)
        return col

    @staticmethod
    def _make_list_widget():
        lw = QListWidget()
        lw.setSelectionMode(QListWidget.ExtendedSelection)
        lw.setDragEnabled(True)
        lw.setAcceptDrops(True)
        lw.setDropIndicatorShown(True)
        lw.setDragDropMode(QListWidget.DragDrop)
        lw.setDefaultDropAction(Qt.MoveAction)
        return lw

    @staticmethod
    def _collect(widget):
        # "*" is used to mark videos with at least one event
        return [widget.item(i).text().rstrip("*") for i in range(widget.count())]

    def categories(self):
        return {
            "unclassified": self._collect(self.list_unclassified),
            "train": self._collect(self.list_train),
            "val": self._collect(self.list_val),
            "test": self._collect(self.list_test),
            "inference": self._collect(self.list_inference),
        }


def run(df: pd.DataFrame, project: dict):
    """Export BORIS observations/events to a FERAL-compatible JSON.

    See https://www.getferal.ai/ > Label Preparation
    """

    def log(msg):
        messages.append(str(msg))

    def safe_float(d, key):
        try:
            return float(d[key])
        except Exception:
            return None

    messages = []

    out = {
        "is_multilabel": False,
        "splits": {"train": [], "val": [], "test": [], "inference": []},
    }

    # ---- Behaviors (FERAL classes) ----
    behavior_conf = project.get("behaviors_conf", {})
    boris_codes = [behavior_conf[k].get("code") for k in behavior_conf]
    boris_codes = [c for c in boris_codes if c]  # drop None/empty

    # Reserve 0 for background. If BORIS has a behavior literally named "other",
    # treat it as background and do not include as a class.
    boris_codes_no_other = [c for c in boris_codes if c != "other"]

    dlg = BehaviorSelectDialog(boris_codes_no_other)
    if not dlg.exec():
        return "Behavior selection canceled; export aborted."

    selected = sorted(set(dlg.selected_codes()))
    if not selected:
        log("No behaviors selected: everything will be mapped to class 0 ('other').")

    class_names = {"0": "other"}
    for i, code in enumerate(selected, start=1):
        class_names[str(i)] = code

    out["class_names"] = class_names
    behavior_to_idx = {code: i for i, code in enumerate(selected, start=1)}

    if selected:
        log(f"Selected behaviors: {', '.join(selected)}")
    log(f"Classes: {class_names}")

    # ---- Iterate observations/videos ----
    labels = {}
    video_list = []

    has_media_file_col = "Media file" in df.columns
    has_subject_col = "Subject" in df.columns

    observations = sorted(project.get("observations", {}).keys())
    if not observations:
        return "No observations found in project; nothing to export."

    for obs_id in observations:
        log("---")
        log(obs_id)

        obs = project["observations"][obs_id]
        media_files = obs.get("file", {}).get("1", [])
        if not media_files:
            log(f"Observation {obs_id} has no video in player 1.")
            continue

        media_info = obs.get("media_info", {})
        fps_dict = media_info.get("fps", {})
        length_dict = media_info.get("length", {})
        frames_dict = media_info.get("frames", {}) or {}

        for media_path in media_files:
            video_name = Path(media_path).name

            if video_name in labels:
                log(f"Duplicate video name '{video_name}' encountered; skipping (obs {obs_id}).")
                continue

            # Filter events for this observation + this media file when possible
            if has_media_file_col:
                df_video = df[(df["Observation id"] == obs_id) & (df["Media file"] == media_path)]
            else:
                df_video = df[df["Observation id"] == obs_id]
                log("Warning: df has no 'Media file' column; using all events from observation.")

            # Enforce single-subject labeling when Subject column exists
            if has_subject_col and not df_video.empty:
                subjects = df_video["Subject"].dropna().unique().tolist()
                if len(subjects) > 1:
                    log(f"More than one subject in {video_name}: {subjects}. Skipping.")
                    continue

            # Mark videos that contain at least one event with "*"
            video_list.append(video_name + ("*" if not df_video.empty else ""))

            fps = safe_float(fps_dict, media_path)
            duration = safe_float(length_dict, media_path)
            if fps is None:
                log(f"Missing/invalid FPS for {video_name}. Skipping.")
                continue
            if duration is None:
                log(f"Missing/invalid duration for {video_name}. Skipping.")
                continue

            if media_path in frames_dict:
                n_frames = int(frames_dict[media_path])
                log(f"{video_name}: fps={fps} duration={duration} frames={n_frames} (BORIS)")
            else:
                n_frames = int(round(duration * fps))
                log(f"{video_name}: fps={fps} duration={duration} frames={n_frames} (rounded)")

            if n_frames <= 0:
                log(f"Non-positive frame count for {video_name}. Skipping.")
                continue

            frame_dt = 1.0 / fps
            labels[video_name] = [0] * n_frames  # default: "other"

            # Fill per-frame labels
            for frame_idx in range(n_frames):
                t = frame_idx * frame_dt
                behaviors = (
                    df_video[(df_video["Start (s)"] <= t) & (df_video["Stop (s)"] >= t)]["Behavior"]
                    .unique()
                    .tolist()
                )

                if len(behaviors) > 1:
                    log(
                        f"{video_name}: overlapping behaviors at frame {frame_idx} (t={t:.6f}s): "
                        f"{behaviors}. Removing video (is_multilabel=False)."
                    )
                    del labels[video_name]
                    break

                if not behaviors:
                    continue

                labels[video_name][frame_idx] = behavior_to_idx.get(behaviors[0], 0)

    out["labels"] = labels

    # ---- Splits dialog ----
    split_dlg = CategoryDialog(video_list)
    if not split_dlg.exec():
        log("Export canceled at split assignment stage.")
        return "\n".join(messages)

    splits = split_dlg.categories()
    splits.pop("unclassified", None)
    out["splits"] = splits

    filename, _ = QFileDialog.getSaveFileName(
        None,
        "Choose a file to save",
        "",
        "JSON files (*.json);;All files (*.*)",
    )
    if not filename:
        log("No output file selected; nothing written.")
        return "\n".join(messages)

    with open(filename, "w", encoding="utf-8") as f_out:
        json.dump(out, f_out, indent=2)

    log(f"Saved: {filename}")
    return "\n".join(messages)