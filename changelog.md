**v. 9.6.6**

* Fixed bug #899

**v. 9.6.5**

* Added a rounding option to Cohen's kappa plugins. The number of decimals for rounding can be negative (with a value of -1, 123.456 will round to 120.0)


**v. 9.6.4 202-08-29**

* changed extension of texgrid files from .textgrid to .Textgrid

* Added concurrent behaviors in IRR Cohen's kappa plugins

**v. 9.6.3 2025-08-26**

* fixed bug #875

* fixed bug #886

**v. 9.6.2 2025-08-05**

* fixed issues #883 and #885

* Added 4 plugins with new implementations of the IRR Cohen's kappa (weighted and unweighted, with or without modifiers)
See https://github.com/olivierfriard/BORIS/tree/master/boris/analysis_plugins


**v. 9.6 2025-07-15**

* Offsets between multiple videos within an observation can be changed during coding (See Playback menu). Feature request #863

**v. 9.5.2 2025-07-15**

* Improved the media file name value in exported events

**v. 9.5 2025-06-12**

* Introduced the possibility to use R plugins

**v. 9.4.1 2025-05-28**

* fixed bug #864

**v. 9.3.4 2025-05-08**

* fixed #849

* improved the **Check integrity** function: added check for media info.

* introduced an option for returning to observation in case of unpaired state events

* removed possibility to automatically fix unpaired state events for observations from pictures


**v. 9.3.3**

* fixed bug #854

* improved behavioral categories management


**v. 9.3.2 2025-04-14**

* fixed bug #851

**v. 9.2.3 NOT RELEASED**

* fix bug in filtering behaviors function

**v. 9.2.2 2025-03-28**

* Fixed volume button icon

* Implemented a function to check if plugins have the same name

**v. 9.2.1 2025-03-18**

* Fixed default windows size on small monitors

**v. 9.1.1 NOT RELEASED**

https://github.com/olivierfriard/BORIS/releases/tag/v9.1.1

* fixed bug #812

* fixed bug #809

**v. 9.1 2025-03-11**

* Introduced the 'Observation interval' option for analysis: the value will be the Observation interval defined during the creation of the observation (if any)


**v. 9.0.8**

* Fixed bug #833

**v. 9.0.7 2025-02-27**

* fixed bug with START and STOP labels for state events when a modifiers coding map was used

**v. 9.0.6 2025-02-17**

* fixed bug #825

**v. 9.0.5 2025-02-10**

* Switched UI from PyQt5 to PySide6

* Added Analysis plugins function (see https://www.boris.unito.it/user_guide/analysis/#plugins)

* Added Project integrity check when project is loaded and saved (can be disabled in Preferences)


**v. 8.27.9 2024-10-07**

* Implemented the inclusion of non coded modifiers in time budget results (time budget, synthetic time budget and synthetic time budget with time bin)

* Fixed bug #564



**v. 8.27.4 2024-08-20**

* Fixed bug #782

* Fixed bug #767


**v. 8.27.3 NOT RELEASED**

* Fixed bug #781

**v. 8.27.2 NOT RELEASED**

* Fixed color of not editable column in ethogram for dark mode

**v. 8.27.1 2024-06-11**

* Fixed bug #754


**v. 8.27 2024-06-06**

* Add option for automatically update BORIS (See Help > Check for updates and news)
If a new version is found, BORIS will ask the user for updating

**v. 8.26.1 2024-06-06**

* Improved the modifier(s) selection with keyboard (thanks to jonaskn)

**v. 8.26 2024-06-04**

* Implemented an option for setting the modifier(s) when the state event stops.

**v. 8.25.1 2024-04-17**

* Fixed bug when importing a Noldus Observer project without modifiers

**v. 8.25 2024-04-07**

* added a mute/unmute button to each media player

* Added **dark mode** to interface (See Preferences > Interface)


**v. 8.24.3 2024-03-29**

* fixed bug in video - audio synchronization

**v. 8.24.2 2024-03-28**

* fixed bug when exporting events from many observations in aggregated format

**v. 8.24.1 2024-02-13**

* fixed bug #716




**v.8.24**

* added import observation events from a spreadsheet file

* improved events table scroll after editing event: the edited event should be visible

* Add option to add frame indexes to all events (for media observation)


**v.8.23 2024-01-29**

* Added possibility to have many subjects with the same key

**v.8.22.20 2024-01-25**

* Fixed bug #707

* Added option for resizing the toolbar (See Preferences > Interface)

* Added new column "Time offset" to tabular events and aggregated events output (Observations > Export events ...)

* Improved import of behaviors and subjects from spreadsheet files: ODS format was added.




**v.8.22.16 2024-01-12**

* Improved the zoom function (thanks to zemogoravla (https://github.com/olivierfriard/BORIS/pull/697):

**v.8.22.15 2024-01-08**

* Improved the time widget: time can now be a date-time (yyyy-mm-dd hh:mm:ss.zzz). For observation longer than 1 week the time will be stored as Unix epoch.

* Fixed issue on time budget by behavioral category when category contains a point event behavior.

* Fixed issues #693 and #698

**v.8.22.6 2023-11-26**

* added check for behaviors and subjects in the find/replace dialog

* Frame indexes are now set automatically after **edit event**, **shift time** and **Add new event** functions.

* Events table was optimized

Regression:

* it is not possible for now to customize the columns in the events table


**v.8.22.4 only on https://github.com/olivierfriard/BORIS/releases/tag/v8.22.4**

* in geometric measurements the media or image directory path is absolute or relative 

* fixed bug on copy/paste events

* frame index can not be longer edited with **Add event** and **Edit event** functions. The new frame index is extracted from the video.

**v. 8.21.10 2023-11-04**

* fix bugs #675 and #676

**v. 8.21.9 2023-11-03**

* fixed error importing ethogram from CSV/TSV (bug #678)




**v. 8.21.8 2023-10-05**

* fixed bugs #660 and #575


**v. 8.21.6 2023-10-02**

* fixed #642



**v. 8.21.5 2023-09-12**

* fixed #635 and #636

**v. 8.21.4 2023-09-12**

* fixed #650 and #621


**v. 8.21.3 2023-09-07**

* Added option for creating media observations from a directory of media files


**v. 8.20.7 2023-09-05**

* fixed bug #647

**v. 8.20.6 2023-09-01**

* fixed bug #640


**v. 8.20.5 2023-09-01**


**v. 8.20.4 2023-07-02**

* Fixed crash during saving project when no space left on device

**v. 8.20.2 2023-06-02**

* Added geometric improvements to observation from pictures

**v. 8.20 2023-06-01**

* The geometric measurements function was improved: the frames with measurements can be saved as JPG images and the Polyline object has replaced the Distance object.


**v. 8.19.4 2023-05-29**

* bug #623 fixed


**v. 8.19.1 2023-05-10**

* Re-introduced the option for stopping the ongoing state events between media and at the end of observation

* Edit selected events function: added possibility to set all subjects to **No focal subject**

* Fixed bug in media navigation after double-clicking in the Events table



**v. 8.19 NOT YET RELEASED**

* fixed bug #614 


**v 8.18.1 NOT RELEASED**

* media added from a directory are now sorted

* re-encode/resize tool expresses the bitrate in Mb

* Implemented scan-sampling for observation from media

* Implemented check of timestamps in the check project integrity function (must be between -2^31-1 and 2^31-1)

* fixed bug #616



**v. 8.17 2023-04-19**

* improved the Zoom function

Now it is possible to:
* zoom in with `CTRL` + `+`
* zoom out with `CTRL` + `-`
* set no zoom with `CTRL` + `0` (or by clicking the mouse right button on the video)

and move (pan) the picture in the video using the following key combinations:
* `CTRL` + `LEFT ARROW`
* `CTRL` + `RIGHT ARROW`
* `CTRL` + `UP ARROW`
* `CTRL` + `DOWN ARROW`, 

If you have an observation with many video players you must select the player you want to zoom/pan with a left-click before.




**v. 8.16.6 2023-04-18**

* 2 issues fixed in synthetic time budget (CSV and XLSX format)

**v. 8.16.5 2023-04-17**

* Fixed bug in About dialog

**v. 8.16.4 2023-04-17**

* fixed bug #604

**v. 8.16.3 2023-03-30**

* Improved error dialog with system info

**v. 8.16 2023-03-23**

* Added behavioral categories custom colors

* fixed bug #599

**v. 8.15 2023-03-21**

* improved the format of geometric measurement results. Results can now be saved in TSV, CSV, XLSX, ODS, HTML, Pandas dataframe (pickle) and R (RDS file).

* Added an option for deinterlacing video (See the Playback menu)


**v. 8.14 2023-03-20**


* added geometric measurements for observations from pictures

* fixed bug in geometric measurements (misplaced coordinates when the player was resized)


**v. 8.13 2023-03-16**

* introduced color choice for behavior. The color will be used for plots

**v. 8.12.2 2023-03-14**

* fixed bug #557

* fixed bug in displayed video rotation function

**v. 8.12 2023-03-10**

* implemented rotation of displayed video (See Playback > Rotation)

**v. 8.11.3 2023-03-03**

* fixed bug #589

* fixed end time in needleman-wunsch function (https://github.com/olivierfriard/BORIS/pull/580)

**v. 8.11.2 2023-02-28**

* fixed bug #582

* fixed bug #583

**v. 8.11.1 2023-02-23**

* fixed bug in observations from audio

* embedded ffprobe utility (from FFmpeg framework) in Windows versions

**v. 8.11 2023-02-23**

* added a frame index column in events table for media observation

* added a **Configure column** option for the events table in order to show/hide columns. Right-click on the horizontal header

* fixed bug #578

* fixed bug #577

* some minor improvements


**v. 8.9.19 2023-02-08**

* improved media file info (ffprobe utility is used if found in same directory than ffmpeg)

* fixed bug during editing event of a pictures observation in view mode

**v. 8.9.18 2023-02-07**

* fixed bug #566

* fixed bug #567


**v. 8.9.16 2023-01-31**

* added an Option for selecting the indentation mode of the BORIS project file (JSON). See Project > Preferences

* fixed bug in Media file name in aggregated events output


**v. 8.9.14 2023-01-20**

* added function for exporting the project as a pickle file: see https://realpython.com/python-pickle-module/ for details

* improved real time events plot: plot is updated after events are edited/deleted/pasted

* improved observations list window for large number of observations

* added exhaustivity for observation from pictures


**v. 8.9.13 2023-01-19**

* changed the BORIS logo (v. 3)

* added choice for bitmap format in **Extract frames** function

* fixed bug in file name in **Extract sequences** function

**v. 8.9.12 2023-01-18**

* fixed bug #560

* Added a merge media files function (see Tools > Media file > Merge media files)

* improved creation of new observation: added check for media file enqueued with more than one player


**v. 8.9.11 2023-01-13**

* improved the aggregated events export format: added column with the media file and media durations


**v. 8.9.9 2022-12-13**

* fixed problem with mpv v.2 on Windows

* fixed bug in export sequences function when time offset was used

* fixed bug in **export events as TextGrid** function when no focal subject was selected

* improved **export events as TextGrid** function


**v. 8.9.5 2022-11-29**

* fixed size of **New observation window** for small screens (height < 800 px)

**v. 8.9.4 2022-11-21**

* improved the output from export tabular events function.

* improved the time interval selection for analysis (time budget, export events ...). The default time interval corresponds now to the coded events

* fixed bug in time budget when independent variables without value


**future version 8.9.2 (NOT released only on PyPI for now)**

* Implemented a parameter for **video hardware decoding** (see Preferences)

* Improved the **Time budget** and **Synthetic time budget** outputs

* Added the possibility to use the **v.2 of libmpv API**

* Added Pandas data frame format to **Time budget** analysis output

* Added RDS format to **Time budget** analysis output (see https://www.rdocumentation.org/packages/base/versions/3.6.2/topics/readRDS)

* Improved the **Media file information** function: non-ascii characters in metadata are now recognized

* Improved the **Export events / tabular format** output


**v. 8.9 2022-10-25**

* Renamed **File** menu in **Project** menu

* moved **Remove media file and images dir path** menu option in **Projects / External files** menu option

* moved **Remove data files path** menu option in **Projects / External files** menu option

* Add "Set paths relative to project dir** menu option (for media files, images dir and data files)

* fixed bug in **Save as** function: the window title is now updated

* fixed bug #542

* fixed bug #548


**v. 8.8.1 2022-09-16**

* added 2 checks for independent variables in **Check project integrity** function

* improved the **Import ethogram from spreadsheet** function

* fixed bug #535



**v. 8.8 2022-09-09**

* Added "Import ethogram from spreadsheet file (Microsoft-Excel XLSX or Open Document ODS)" function.

* Added BORIS project to the Export ethogram function outputs

* Fixed current observed behaviors after event editing 


**v. 8.7 2022-09-02**

* Added point events to the Praat TextGrid export format (as TextTier)

* Added color selector for the geometric measurement marks

* Added total coded duration by subject by observation in the aggregated events export format

* Added Pandas dataframe (pickle) output to aggregated events export function

* Added R dataframe (readRDS) output to aggregated events export function

* fix bug #523



**v. 8.6.8 2022-08-29**

* Added function for coding from a directory containing pictures (See New observation > Observation from pictures)

* modified the **Export aggregated events** output
    * added an observation type column
    * added image index and image file path columns

* added check pictures directory to the **Check project integrity** function

* Added option for setting the media file name (without path) as observation id

* Added option for setting the picture directory name (without path) as observation id

* Added **synthetic time budget** and **synthetic time budget by time bin** visualization and option for saving results

* Fixed various bugs in **Geometric measurements** function

* fixed bug #527

**v. 8.6.5 2022-08-01**

* fixed bug #519

* fixed bug #520

**v. 8.6.3 2022-07-29**

* Added a star to project name (or project file name) in the window title when the project was modified and not saved.

* Fixed bug #517

**v. 8.6.2 2022-06-16**

* implemented feature request #502 The 'Delete all events' option is now only in the **Observations** menu.

* Improved the Undo function. A menu option was added in the **Observations** menu.

* Fixed the time for automatically closing an excluded event (again at -0.001 s)

* Fixed bugs #500 and #503

* Fixed bug when double-click on the Modifiers cell during editing project


**v. 8.6.1**

* fixed bug #468

**v. 8.5**

* introduced an Undo function for events coding (25 levels)

* fixed bug #493

**v. 8.4.1 2022-05-16** 

* fixed bug https://github.com/olivierfriard/BORIS/issues/492


**v. 8.4 2022-05-13** 

* added experimental latency function (for one observation)

* fixed bug when closing observation

**7.13.9 2022-10-25**

* fixed bug #548

**7.13.8 2022-07-27**

**7.13.7**

* fixed bug #507


**7.13.6**

* fixed bug #493



**7.13.5 2022-05-12**

* minor changes


**7.13.4 2022-05-08**

* fixed regression introduced in v. 7.13.3 (bug #485 and #486)

* some modifications for running with Python 3.10




**7.13.3 2022-05-02**

* improved error reporting system: the boris_error.log is no more cancelled when BORIS is restarted

* fixed bug #483


**7.13 2022-02-22**

* added modifiers to the **export ethogram** function (request #448)

* code cleaning


**7.12.2 2021-09-20**

* Improved the coding pad: color mode (by behaviors or behavioral categories), buttons color and font size can be customized. See Preferences > Plot color


**7.11.1 2021-09-09**

* The geometric measurements were improved: all coordinates, distances and area are now referred to the original video resolution.


**7.10.7 2021-07-12**

* enhanced the video duration detection
* code cleaning

**7.10.5 2021-05-12**

* increased max play rate to 30 (feature request #395)

* fixed bug when observations list was opened and the project is empty (no observations)


**7.10.4 2021-05-10**

* fixed bug in Export behavior binary table function (#393)

**7.10.3 2021-04-28***

* fixed bug #367 and #386

* fixed bug in project conversion function


**7.10.2 2021-01-16**

* added synthetic time budget with time bin
* The **observations list** window remembers its last position and size
* Added a new column to the **observations list** (observation duration) that contains the duration of observation (difference between the last observed event and the first observed event)
* The observations with unpaired events are displayed with a light red background in the **observations list**
* added exhaustivity percent to the **observations list**


**v. 7.9.24 2020-12-18**

* added more info in About... window

* fixed bug #344
* fixed bug #347 (bug was present only on Windows version)
* fixed bug when the user tries to save the project on a protected directory

**v. 7.9.21 2020-11-16**

* added seconds to the date and time in Observation window

* added option for using EPOCH time (seconds since 1/1/1970) when using current time (bug #333)

* fixed bug #341

**v. 7.9.19 2020-09-08**

* migrated python-intervals module to portion module

* fixed missing modules previously imported by tablib: MarkupPy, openpyxl, odfpy, xlrd and xlwt



**v. 7.9.16 2020-08-28**

* code cleaning

* improved error message

* fixed bug #305

* fixed bug #306


**v. 7.9.15 2020-07-10**

* added compressed format for project files (.boris.gz). The file dimension can be reduced up to 15 times

* remove the project files that are not accessible from the Recent projects menu.


* fixed bug in ffmpeg path

* fixed bug when an observation is closed after state events reparation (Thanks to Haaken Zhong Bungum)

* fix bug when ethogram, subjects list or independant variables list are edited after sorting (Thanks to Jana Muschinski)


**v. 7.9.8 2020-03-13**

* Improved the media file checking when creating a new observation.

* Added a **Point** element on the **Geometric measurements** tool

* Fixed bug during sequence extraction: the video file format is maintained in the output

* Removed the splashscreen for MacOS (in certain conditions it can cover the first use dialog box).



**v. 7.9.7 2020-01-14**

* Added "No focal subject" in observations list (if necessary)

* Fixed the 2-frames bug (https://github.com/olivierfriard/BORIS/issues/169)

* fixed bug when a video offset is set in frame-by-frame mode

* fixed regression in geometric measurements function


**v. 7.9.6 2019-12-05**

* Introduced the possibility to extract frames in memory instead of saving them in a temporary directory

* Fixed the **File not found s_0_??? bug** on MacOS



**v. 7.9.4 2019-11-21**

* Added point events to **behavior binary table** output

* Added new format for **behavioral sequences export**: unique sequence with subject name

* Fixed bug #252 


**v. 7.9.3 2019-11-15**

* Fixed bug in Preferences (program crash)

**v. 7.9.1 2019-11-04**

* Improved the start and end time selection for analysis. Time can now be greater than 24h.

* fixed bug in **Advanced event filtering** function (crash)

**v. 7.9 2019-10-25**

* Added an option to lock the dock widgets on the main window (Ethogram, Subjects and Events)
(See Tools > Lock dockwidgets)


**v. 7.9 RC2 2019-10-24**

* Added time budget bar plot for durations and number of occurences of behaviors

* Added behaviors defined as point event to the **Advanced event filtering** function

* Fixed bug in **Export events as Praat textgrids** function

**v. 7.9 RC1 2019-10-15**

* Added compact format for time budget (See Preferences > Results) 

* Added XLS, ODS, XLSX formats for saving results of **Advanced event filtering** function

* Changed keys for play rate adjustment (Home, End and Backspace).

* Fixed bug when the observation id contain done or many dots (.)



**v. 7.8.4 2019-10-03** 

* Added the **Behavior Binary Table** format for exporting the coded events (See Analysis > Behavior Binary Table)

* Added the **Advanced event filtering** function (See Advanced event filtering)

* Added keyboard shortcuts for play rate adjustment ([, ] and backspace) (kdquine contribution)

* Modified the jump back/forward function: the video seeking is now based on the current play rate (kdquine contribution)


**v. 7.8.2 2019-09-05**

* added **Find events** and **Plot current observation** buttons on the toolbar

* fixed bug in synthetic time budget function when more than one behavior is excluded from the total time



**v. 7.8 2019-08-30**

* added **Image overlay on video** function. See https://boris.readthedocs.io/en/latest/#image-overlay-on-video

* added a **time interval option** for limiting the observation (for media based and live observations)


**v. 7.7.5 2019-08-22**

* fixed bug when observation is closed while playing frame-by-frame mode

**v. 7.7.4 2019-08-16**

* fixed bug in **fix unpaired events** function

* fixed bug when exporting many observations in xlsx without grouping them

* fixed issue when **# character** (hash) present in media file path

* fixed issue in **autosave** function


**v. 7.7.3 2019-06-18**

* Fixed severe regression introduce in v.7.7.1 on **time budget**, **plot events** and **export events** functions

**v. 7.7.2 2019-06-14**

* Added option for live observations to **start from current time**

* Fixed bug when importing behaviors from a BORIS project 

**v. 7.7.1 2019-06-13**

* Improved the warning message before **time budget** , **plot events** and **export events** 

* Bug in **event editing** fixed

* Bug in **Export events for JWatcher analysis** function fixed


**v. 7.7 2019-06-04**

* Improved the time editing function. Time over 24h or negative time can now be edited.

* Fixed bug in **modifier from external data** function (crash when external value is not present)


**v. 7.6.1 2019-05-21**

* Fixed bug in **Export observations list** function

**v. 7.6 2019-05-18**

* Added the **Record value(s) from external data file** function. The recorded values are stored in modifier(s) defined as **Value from external data file**. The variable name must be the same than the plotted variable.

* Added the **Import behaviors from clipboard** function (in project window)

* Added the **Import subjects from clipboard** function (in project window)

* Added **Remove all subjects** function (in project window)

* Added warning message before editing the project when observations are already existing.

* Added the **Load modifiers from file** in project window (plain text file)

* Added the **Sort modifiers** in project window (plain text file)

* Added function for selecting the modifiers using the first letter (when no code are defined)

* Fixed bug in **Remove all behaviors** function


**v. 7.5.3 2019-04-11**

* Fixed bug in the **Export events for JWatcher analysis** function

* Fix bug in **Remove all behaviors** function.

**v. 7.5.2 2019-04-08**

* Fixed observation length when last event is recorded after media file length

* Modified the automatic backup function: an automatic backup is done only when the project filename is defined (and an observation is running).

* fixed bug in frames extraction function when a time offset is set

**v. 7.5.1 2019-03-30**

* fixed bug in frames extraction menu option


**v. 7.5 2019-03-30**

* added **Needleman-Wunsch similarity** between observations

* added **extraction of frames** corresponding to coded events.

* Fixed bug #186 (https://github.com/olivierfriard/BORIS/issues/186)

* Fixed bug in sequence extraction function when media file is a wav file.


**v. 7.4.15 2019-03-27**

* fixed bug in IRR Cohen Kappa

* fixed bug introduced in v.7.4.14 in the behavior exclusion function.


**v. 7.4.14 2019-03-20**

* remove current media time from status bar

* fixed bug #177 (Incorrect displaying of current behaviours with modifiers)

**v. 7.4.13 2019-03-15**

* added sound waveform visualization

**v. 7.4.12 2019-03-12**

* Added check for media length availability in **Check project integrity** function

* fixed bug #166 (https://github.com/olivierfriard/BORIS/issues/166)

* fixed extracting WAV file from a WAV media file.


**v. 7.4.11 2019-02-28**

* fixed bug with log generation on Mac

**v. 7.4.10 2019-02-25**

* fixed bug for projects containing modifiers with leading/trailing spaces

* added check for presence of leading/trailing spaces in modifier in the **Edit project window**.

* added check for presence of leading/trailing spaces in the **Check integrity project** function


**v. 7.4.9 NOT RELEASED**

* improved log for debugging version

* fixed bug in video slider in frame-by-frame mode


**v.7.4.8 NOT RELEASED**

* improved presentation of media file in observations list window and edit project window

* improved frame-by-frame mode


**v.7.4.7 2019-02-05**

* Added option for selecting a time interval when exporting events as **aggregated events**

* fixed bug in multi rows description when exporting events as behavioral sequences/strings


**v. 7.4.6 2019-02-01**

* fixed crash on open Preferences (regression in v.7.4.5)


**v. 7.4.5 2019-01-31**

* Added option for **subtitles visualization** (the subtitles file must have the same base name than the video file with a **.srt** extension) (See File > Preferences)

* Fixed bug in the **Synthetic time budget** analysis with arbitrary time interval.



**v. 7.4.4 2019-01-25**

* Introduced a **Refresh preferences** option. See File > Preferences

* Fixed the **invisible player bug**

**v. 7.4.3 2019-01-23**

* Fixed bug in time budget when excluding behaviour durations from total time of observation.

* Fixed bug on updating spectrogram and data when video is paused

**v. 7.4.2 2019-01-16**

* Improved **Play sound on key pressed** and **Beep every...** functions (See **Preferences**)

* Added behavioral categories in **Export events** and **Export aggregated events** functions output

* Fixed bug in **Delete selected events**, **Delete all events**, **Copy events**, **Edit selected event(s)**, **edit time of selected event(s)** (now renamed **Shift time of selected event(s)**) functions when events are filtered.



**v. 7.4.1 2019-01-14**

* Added time and frequency intervals customization  for plotting sound spectrogram.
See Preferences and widgets in the spectrogram window.

* Fixed player visualization problem when upgrading to v. 7 (under certain conditions).




**v. 7.4 2018-12-17**

* Added function for importing project from a Noldus The Observer XT template (otx or otb extensions)
See https://boris.readthedocs.io/en/latest/#import-a-project and  https://www.noldus.com/coding-scheme-exchange/overview


* Added an **Explore project** function
See https://boris.readthedocs.io/en/latest/index.html#explore-project for details

* Improved Find in events and Find/Replace in events functions: added **case insensitive mode**

* Fixed bug when trying to add media or data file without saving the full path when project was not saved.

**v. 7.3.2 2018-12-07**

* fixed bug in focus video area function

**v. 7.3.1 2018-12-06**

* fixed bug when saving position of widgets


**v. 7.3 2018-12-03**

* added a **focus video area** function: click on video will center the video on the clicked point and visualize the video with its native resolution, another click will restore the full video

* The positions of all docking widgets are now saved in the config file (.boris in your home directory)


**v. 7.2 2018-11-30**

* improved ffmpeg processes (functions **resize/re-encode video** and **rotate video**)

* improved spectrogram visualization

* Find and Find/Replace functions apply now only on filtered events (if any)

* fixed bug in ethogram visualization in project window

* fixed bug in subtitles creation (when project was not saved)




**2018-11-20 v. 7.1.4**

* fixed bug in spectrogram generation under MacOS and Linux.

**2018-11-15 v. 7.1.3**

* fixed regression introduced in 7.1.2

**2018-11-15 v. 7.1.2**

* fixed bug in export events as behavioral strings/sequences when modifiers are included

* fixed bug in **time budget by behavioral category** function when many observations are selected and without grouping.

* fixed number of decimals in **time budget by behavioral category** function


**2018-11-13 v. 7.1.1**

* fixed regression in export aggregated events in v. 7.1

**2018-11-13 v. 7.1**

* the aggregated events are now sorted by start time.

* added "Edit time of selected event(s)" function: a time value can be added or subtracted to all selected events of the current observation.

* added "Copy/paste" function for events: events can now be copied/pasted to another observation. Events can also be copied from another source if organized in 5 columns separated by TAB character (time, subject, behavior code, modifiers, comment).

* fixed bug in export aggregated events for SDIS format


**2018-11-09 v. 7.0.14**

* fixed bug in **check update** function.

**2018-10-28 v. 7.0.13**

* fixed bug in frame-by-frame mode: previous frames were not loaded

**2018-10-16 v. 7.0.12**

* added option for subtracting duration of selected behaviors (like "out-of-view" / "out-of-sight") from time budget analysis

* fixed bug when exporting observation with certain characters in id (\\/) as textgrid 

**2018-09-20 v. 7.0.10**

* Added option for adding all defined **subjects as modifiers**

* Added sorting function to ethogram (without editing the project)

* Fixed bug in **Save project** and **Save project as...** functions when no extension (.boris) were given.

* Fixed bug when verifying project modification

* Fixed bug in export events as behavioral strings: not selected events were exported


**2018-09-13 v. 7.0.9**

* added an events filter based on behaviors and/or subjects. Right-click on the events widget > Filter events 

* removed the 'Detach frame viewer' option from preferences. All widgets can be undocked and redocked.

* Fixed scroll to current event function



**2018-09-10 v. 7.0.8** 

* improved **exclusion matrix**: checkboxes of an entire row can be checked or unchecked

* fixed bug in **Coding pad**
 

**2018-09-05 v. 7.0.7**

* added a **rename behavioral category** option

* fix bug when observation closed and re-opened ("event already exists...")


**2018-08-27 v. 7.0.6**

* new logo

* added possibility to delete all selected media files or all selected data files at once

* removed the the **Pause** button. Added the **Pause** command to the **Play** button.

* improved the **Add/Edit event** function: added a button for setting the time with the current media time

* Added "No focal subject" item to the subjects list

* added a **Close observation** button in the toolbar (x)

* bug fix: the position slider is now removed when observation is closed

**2018-08-24 v. 7.0.5**

* added possibility to use upper and lower case keys for coding behaviors and subjects

* the possibility to use up to 8 media file players

* an export format for analysis with JWatcher

* fixed a bug when the 'Alert when no focal subject is selected' option is used.


**2018-09-18 v.6.3.9**

* Fixed bug in export events as behavioral strings: not selected events were exported

* Fixed bug with VLC libraries in Linux versions


**2018-08-24 v.6.3.7**

* fixed bug in media file information in certain conditions



**2018-07-13 v.6.3.6**

* fixed bug when media files are stored in a network



**v.6.3.5**

* fixed a bug in 'Cancel modifier' function.


**2018-06-27 v.6.3.4**

* A bug was found in the 'Stop ongoing state events between successive media files' function. Please do not use it for now. This function was disabled from the v. 6.3.4



**2018-06-14 v.6.3.3**

* fixed bug in export aggregated events function for SDIS format


**2018-06-14 v.6.3.2**

* fixed bug in export events/time budget function (for xlsx format). Module openpyxl was downgraded to v. 2.4.9 for compatibility with tablib module v. 0.12.1


**2018-05-30 v.6.3.1**

* fixed a bug in "Next media" function

**2018-05-28 v.6.3.0**

* Frame-by-frame mode improved: the user can select the cache size (in seconds) for frames extraction. May be useful for large video or video with high FPS value.

* Added main window geometry and state saving/restoring

* Added a "Fix unpaired state events" function

* Added video rotation tool (See **Tools** > **Rotate video**): video can be rotated CW, CCW or 180°

* VLC updated to v. 3 for executable versions 

**2018-04-25 v.6.2.4**

* fixed bug when "sage" colors (sage, darsage, lightsage) were used in plot. These colors were removed from matplotlib colors list

**2018-04-17 v.6.2.3**

* fixed bug in sound spectrogram visualization when the media file path is not stored


**2018-04-04 v.6.2.2**

* fixed bug when importing the ethogram from another project file.

**2018-03-28 v.6.2.1**

* fixed bug in **Transitions matrix** function

**2018-03-26 v.6.2**

* improved the **View observation** mode

* removed the old Plot events function (_Plot events for back-compatibility_ for a bug that occurs in certain conditions when behaviors without events were excluded from plot)

* Improved the **Synthetic time budget** function: added **duration mean**, **duration std dev** and **proportion of time** parameters

* Added an **Observations list** icon in the toolbar to open the **Observation list** window.
Clicking again on this button will not close the window (for now).

* Added **plot events** function to **BORIS Command Line Interface**

* Improved "extract media sequences corresponding to events" function

* Fixed bug in **Plot events** function. In certain conditions behaviors were not plotted.



**2018-03-14 v.6.1.6**

* fixed bug in **export aggregated events** in certain conditions (behavior with different modifiers that were not exclusive)

* fixed regression in **Exclusion matrix**

**2018-03-09 v.6.1.5**

* Fixed regression in plot events 1 (legacy)


**2018-03-09 v.6.1.4**

* Added control of format for the **Start time** value for plot of external data files

* Added control of media files availability in **Check project integrity** function

* improved the **BORIS Command Line Interface** (**boris_cli**): added the **check_project_integrity** function

Type ``boris_cli --command list`` from a terminal to obtain the list of available functions:

    check_state_events
    usage:
    boris_cli -p PROJECT_FILE --command check_state_events 
    
    export_events
    usage:
    boris_cli -p PROJECT_FILE --command export_events [OUTPUT_FORMAT]
    where:
    OUTPUT_FORMAT can be tsv (default), csv, xls, xlsx, ods, html
    
    irr
    usage:
    boris_cli -p PROJECT_FILE -o "OBSERVATION_ID1" "OBSERVATION_ID2" --command irr [INTERVAL] [INCLUDE_MODIFIERS]
    where:
    INTERVAL in seconds (default is 1)
    INCLUDE_MODIFIERS must be true or false (default is true)
    
    subtitles
    usage:
    boris_cli -p PROJECT_FILE --command subtitles [OUTPUT_DIRECTORY]
    where:
    OUTPUT_DIRECTORY is the directory where subtitles files will be saved
    
    check_project_integrity
    usage:
    boris_cli -p PROJECT_FILE --command check_project_integrity


* Fixed bug when external data file has only one column (crash)



**2018-03-07 v.6.1.3**

* Fixed bug: focal subject was not recorded

**2018-03-07 v.6.1.2**

* Added a **Check project integrity** function (File > Check project integrity). Various controls are made on the current project: States events unpaired, behaviors in observations that are not in ethogram, behaviors that belong to behavioral categories that are not in behavioral categories list.

* Improved "Find in events" function

* Added a control when behavioral categories are deleted.
BORIS will warn if behaviors belong to a deleted category and will propose to remove those behaviors from the deleted behavioral category.

* GNU/Linux: Added executable version based on Ubuntu 16.04.3 LTS

* Fixed bug in "Stop ongoing state events between successive media files" for behaviors with modifiers.



**2018-03-02 v.6.1.1** 

* Added **View observation** feature. The coded events can be visualized and modified without the possibility to log events with keyboard or pads. The media files will not be available.

* Added the possibility to do not store the media file paths in the BORIS project. In this case the media file(s) must be in the same directory than the BORIS project file. This option can be used if you are coding from various computers on the same projects and media files or if you want to move your media files. See the user guide at http://boris.readthedocs.io/en/latest/#media-based-observation



**2018-02-23 v.6.1 PRE-RELEASE** 

* Added **recent project files menu**

* Added **command line interface** function (see boris_cli.py script). Equivalent functions were removed from boris.py.

To obtain a list of available commands:

``python3 boris_cli.py -p test.boris -o "observation #1" --command list ``


* Added bigger timer at top of the main window

* Added option for exporting observations in single files for export aggregated events function 

* Added **XLSX format** to Ethogram export

* Fixed bug in ethogram editing (remotion of a behavior and editing of the last one crash)



**2018-02-09 v.6.0.6**

* updated embedded ffmpeg to fix problem with PNG format

**2018-01-29 v.6.0.5**

* fixed bug in IRR Cohen's Kappa function

**2018-01-27 v.6.0.4**

* Added **Save results** function in Results window dialog

* fixed bug in IRR Cohen's Kappa function

**2018-01-24 v.6.0.3**

* bug in start observation fixed. Bug were introduced in v. 6.0.2

**2018-01-24 v.6.0.2**

* Cohen's Kappa IRR improved: it is now possible to include the modifiers in analysis. 'K = nan' bug fixed. The default value for interval is now 1 second.


**PRE RELEASE 2018-01-21 v.6.0.1**

https://github.com/olivierfriard/BORIS/releases/tag/v6.0.1

* Added function for plotting external data synchronously with media file.
Data are read from plain text files (TSV, CSV ...) containing timestamp values.
The sampling rate can be variable.

**2017-12-14 v.5.1.3**

* Fixed bug in time budget analysis in certain conditions
* Fixed bug in "Jump to specific time" in frame-by-frame mode


**2017-11-20 v.5.1.0**

* Added **Behaviors coding map**: behaviors can be coded by clicking on regions defined over an image

* Added **subjects coding pad** (like a coding pad for subjects)

* Coding pad contains now only the filtered behaviors

* Fixed bug in **plot function** with observations containing only point events


**2017-11-10 v.5.0.1**

* fixed bug on behaviors order on the coding pad.


**2017-11-09 v.5.0.0**

* Added a **Synthetic time budget** function. A synthetic time budget for all selected observations is created in TSV, CSV, ODS, XLSX, XLS, HTML formats. 2 parameters are available at the moment: total duration (for state behaviors) and number of occurrences.

* Added **XLSX format** to "export events" functions and time budget export

* Added check for empty subject names and empty independent variable labels

* Removed the addition of the correct file extension to file name for the selected file format.

* Improved time budget function.

* Time budget results: changed "-" to "NA" in duration field when behavior is defined as "state event" 

* Added duration value for state events in "export aggregated events" function

* Added **plot colors personalization**: File > Preferences > Plot colors
see https://matplotlib.org/api/colors_api.html and https://matplotlib.org/examples/color/named_colors.html

* Added total duration of observation in export events and export aggregated events functions

* EXPERIMENTAL: Added some parameters to the command line. Run boris.py -h or boris.exe -h for details
Some analysis can now be done in batch with the action parameter (--action / -a).
For example the command:

.. text
    python3 boris.py -p project.boris -o "obs #1" -a "check_state_events_obs"

will output the status of state events of the "obs #1" observation of the project.boris project.

Bugs fixed

* Mac version: the type of the independent variable can be changed

* Fixed bug in time budget tool in certain conditions





**2017-10-01 v.4.1.11**

Changes

* Added functions for selecting/unselecting behaviors in exclusion matrix.
* Added new events plot: Subject are plotted in different plots on one figure.
* IRR menu option moved under **Analysis > Inter-rater reliability > Cohen's kappa**
* New **about...** dialog: program versions are now hidden.

Bugs fixed


* fixed bug in events plot function: the behaviors are now plotted with modifiers (if selected)
* fixed bug in IRR with live observations


**2017-09-22 v.4.1.10**

* fixed a bug when subjects are filtered

**2017-09-20 v.4.1.9**

* fixed bug when "multiple selection" modifiers are used and no selection is made


**2017-09-20 v.4.1.8**

* fixed bug on spectrogram generation from observation window (only Microsoft Windows versions).

* fixed bug after removing the last independent variable. Edit fields were not cleared

* fixed bug when an old version of matplotlib is used (crash when generating spectrogram using the **Viridis** color map) 

**2017-09-14 v.4.1.7**

* fixed bug in sound spectrogram visualization

**2017-09-07 v.4.1.6**

* fixed crash when a modifiers coding map was defined

**2017-08-31 v.4.1.5**

* Added check function for length of video

* fixed bug when frame rate >= 100 FPS

* fixed bug when multiple selection modifiers contain a shortcut


**2017-07-18 v.4.1.4**

* Added an "Export ethogram" function (TSV, CSV, XLS, ODS, HTML formats supported).

* Fixed bug when opening old projects without behavioral categories


**2017-07-10 v.4.1.3**

* fixed bug in "resize/re-encode" function

**2017-07-07 v. 4.1.2**

* fixed bug in modifiers setting

**2017-05-24 v. 4.1.1**

* added the Inter Rater Reliability index (Cohen's Kappa) (available for 2 selected observations)

* fixed bug in extract sequences from media file function

* fixed bug when a modifiers' set was removed

* Improved the *import observations* function


**2017-05-24 v. 4.0.3**

* modified the independent variable editor: the variables can no more be edited into the table.

* add new independent variable format: timestamp (YYY-MM-DD HH:mm:ss)

* add new modifier type: numeric (accepted values are integer and float)

* add new modifier type: multiple values

* added possibility to delete many observations in one operation

* Improved the "check state" function

* Improved the "view behavior" function

* Improved the **Project server** function. The server runs until it is shutdown or timed out.

* Improved the "View behavior" function (context menu of Ethogram table)

* fixed some bugs

* added function for checking news from BORIS web site. The function is triggered when the version is checked from BORIS web site. See Preferences.

* added function for renaming independent variables that already exists during import.

* changed version format to x.y.z



**2017-03-24 v. 3.60**

* Added option for stopping current state events independently of modifiers (see File > Preferences > Project).

* Added the "Project server" function to send and receive project/observation to/from the http://boris-app.readthedocs.io/[BORIS App]



**2017-03-22 v. 3.52**

* Fixed bug in the "edit event" function when an offset was defined.

**2017-03-14 v. 3.50**

* Fixed bug when observations with id containing characters \/*[ ]:? were exported in Microsoft Excel format. These characters are forbidden in Excel worksheet name and are now replaced by spaces.

* Fixed bug in sorting observations by numerical independent values. Independent variables values were sorted as strings.

* Fixed bug in observations list when independent variable value not assigned


**2017-03-08 v. 3.49**

* Added option for selecting the bitmap format for frame in frame-by-frame mode (**JPG** for low quality/low disk space requirements and **PNG** for high quality/high disk space requirements). See **File > Preferences > frame-by-frame mode**

* Added dialog for filtering subjects in subjects list (right-click in subjects list)

* fixed bug when resizing frame in frame-by-frame mode



**2017-03-02 v. 3.48**

* improved observations list with filter

* Add option for beeping every n seconds of media file (see Preferences to set n).

* fixed behaviors order in time budget, plot events, coding_pad.


**2017-02-20 v. 3.47**

* fixed another bug in SDS export function when independent variables were set

**2017-02-17 v. 3.46**

* fixed bug in SDS export function when independent variables were set

**2017-02-17 v. 3.45**

* fixed bug that crashes BORIS when behavioral categories were not set in certain conditions.

**2017-01-16 v. 3.44**

* added check for trailing spaces in subjects names, behavior codes and behavioral categories.

* fixed bug in remove media function for old projects

* fixed bug in behavioral strings and transition matrices generation when behavior codes contain spaces

**2017-01-09 v. 3.43**

* added behavioral categories when importing ethogram from another project

**2017-01-07 v. 3.42**

* fixed bug when ffmpeg path contain spaces

**2017-01-02 v. 3.41**

* added compatibility with Python 3.6. Updated the embedded tablib module to v. 0.11.4

**2017-01-27 v. 3.4**

* Added 2 parameters for spectrogram visualisation: the *spectrogram height* (in pixel) and the *spectrogram colors map*. See *File > Preferences > Spectrogram*

The available colors map are: viridis, inferno, plasma, magma, gray and YlORd. (see http://matplotlib.org/examples/color/colormaps_reference.html for details). 

* Added check function for already existing files during re-encoding / resizing of video.

* Fixed regression on Windows: Re-encoding / resizing video and spectrogram generation functions were not working.

* Fixed bug when the Cancel button of a modifiers coding map was pressed

* Fixed bug in "export events as behavioral strings" function.

**2017-01-23 v. 3.3**

* added separate zoom functions for the media players. See **Playback > Zoom player**

* added a function showing the BORIS reference. See **Help > How to cite BORIS**

* Modifiers are now conserved when type of behavior is modified in ethogram

* fixed bug in Cancel function during selection of modifiers

* fixed bug when modifier contains a comma (,). The characters not allowed in modifiers are:
**( ) |** and **,**

*2016-12-16 v. 3.2*

* added frame-by-frame mode for two simultaneous player

* added option for detaching the frame viewer(s)

* added independent variables in behavioural strings output

* added independent variables in "aggregated events" output

* extended "Check state events" function on selected observations

* rounded frequencies of transition to 3 decimals

* fixed bug in spectrogram generation when media file not found

*2016-11-24 v. 3.12*

* fixed bug in "Plot events" function when modifiers are included


*2016-11-23 v. 3.11*

* fixed bug in "find/Replace in events" function


*2016-11-21 v. 3.1*

* added "Find in events" function 

* added Find/Replace function for events

* improved "Extract sequences from media file" function

* improved the generation of spectrogram from observation window

* improved the "edit selected events" function: subjects and behaviors must be chosen from a list a values

* fixed bug in "edit selected events" for selection of one event

* fixed bug in determination of START/STOP for state events with modifier(s) 



*2016-11-04 v. 3.0*

* improved the generation of spectrogram

* improved program closure: all tool windows are automatically closed before exiting (coding pad, spectrogram, etc)

* fixed bug with left/right arrow keys in frame-by-frame mode. Keys not worked after main window looses the focus

* fixed bug in time display after coding behavior in frame-by-frame mode

* fixed bug in "export events" function when observation has negative offset

* fixed bug in "import independent variables" function



*2016-10-27 v. 2.999*

* added 2 new transitions matrix output: numbers of transition matrix and frequencies after behavior matrix

**2016-10-21 v. 2.998**

* fixed bug that crash BORIS in dual video mode on Mac OS


**2016-10-17 v. 2.997**

* added function for importing one or more observations from a BORIS project file into the current project. See **Observation > Import observations**.

* added independent variables values to single time budget for multiple observations

* added parameter for resizing the extracted frames from video file in frame-by-frame mode. Resizing the frame enhance this mode for high resolution video (like 1980x1080).
See **File > Preferences > frame-by-frame**

* Other improvements to the frame-by-frame mode.



**2016-10-07 v. 2.996**

* added function for creation of normalized transitions matrix:

See **Observations > Create transitions matrix**

example of normalized transitions matrix:

	        jump	walk	drink	groom
    jump	0.3	0.0	0.0	0.1
    walk	0.0	0.0	0.2	0.0
    drink	0.2	0.0	0.0	0.0
    groom	0.0	0.2	0.0	0.0


* added function for creating https://en.wikipedia.org/wiki/DOT_(graph_description_language)[DOT scripts] from normalized transitions matrix files.

See **Tools > Transitions flow diagram > Create transitions DOT script**

The DOT script can used with http://www.graphviz.org/[Graphviz] or http://www.webgraphviz.com/[WebGraphviz] to generate flow diagram

* added function for creating flow diagram (if Graphviz is installed and dot program is available on path)

See **Tools > Transitions flow diagram > Create transitions flow diagram**

Example of flow diagram displaying the fraction of the total number of transitions on the edges of the graph:

image::https://github.com/olivierfriard/boris_docs/blob/master/flow_diagram_graphviz.png[flow diagram example]

* fixed behaviors colors in plot events  (https://github.com/olivierfriard/BORIS/issues/50)

* fixed double "cariage return" bug when exporting plain text file on Windows 

**2016-10-03 v. 2.995**

* fixed bug in the "Time budget by behaviors category" function


**2016-09-28 v. 2.994**

* added function for re-encoding and resizing video files with the included ffmpeg program

* improved the "media file information" function. Information can be obtained from any media file (without having to create an observation). Information is obtained by the included ffmpeg program and is available on Windows platform too.

* fix bug that cause crash when changing video to the next one (enqueued video mode)


**2016-09-12 v. 2.993**

* added export observations in SDIS format (for analysis with the GSEQ program (http://www2.gsu.edu/~psyrab/gseq)


**2016-09-07 v. 2.992**

* fixed bug in "Excluded behaviors" column in project window. this bug was introduced with the behaviors categories.

**2016-09-05 v.2.991**

* added sorting function for observations in **Observations list**. Observation can be sorted ascending or descending by observation id, observation date, description, subjects or media files.

**2016-09-01 v.2.99**

* added behavioral categories: behaviors can now be organized in categories: It is now possible to group behaviors by category for the time budget analysis.
**See Behavioral categories** button in the **Ethogram** window

* added a coding pad: all behaviors are organized in buttons on a window (pad) and can be selected by clicking.
This feature should be useful for users that are using a touch screen tablet (like Surface).
If behavior categories are defined the behavior button color will reflect the category of behavior.
See **Tools -> Coding pad**

* improved the "geometric measurements" function: measurement schemes can now be persistent between frames
* improved the "Export events" function: added CSV, XLS, HTML and ODS formats for exporting
* improved the "Export aggregated events" function: added CSV, HTML, XLS and ODS formats for exporting
* improved the "Save results" function of Time budget windows: added TSV, CSV, XLS and ODS formats
* improved the visualization of dialog window: they are now always on top

**2016-06-30 v.2.981**

* modified "Export events as strings" function: modifiers can be added to behaviors.


**2016-06-03 v.2.98 EXPERIMENTAL**

* added function for filtering behaviors in ethogram: behaviors not used in observation con be hidden 
* added new type of independent variable: "set of values" allow the observer to choose a value in a set of predefined values. (for example: the "meteo conditions" variable can be "rainy","sunny", "cloudy" etc)

* fixed bug when exporting events in XLS format for observations with id longer than 31 characters
* fixed bug in export events function for live observations


**2016-05-05 v.2.97**

* added inter-events statistics in time budget function when more observations are analyzed
* improved analysis and export functions: introduced a time interval selection to restrict analysis/export
* added "scan sampling" function to live observation. See user guide for details

* fixed bug in "Export events as Praat textgrid" 
* fixed bug in export function: modifiers were not exported anymore
* fixed bug in Subject legend in "Plot events" function


**2016-04-12 v.2.96**

* added HH:MM:SS format for time axis in plot events function*
* fixed bug when opening old project file.


**2016-03-30 v.2.95**

* fixed bug in editing observation function when media file were not available


**2016-03-22 v. 2.94**

* removed limitation on key: a same key can be used for coding a behavior or a subject. BORIS will pause the media file and ask user to choose between behavior or subject.
* Improved the modifiers editing function: modifiers and set of modifiers can now be manually sorted. Function keys (F1, F2 ... F12) can be used as shortcut keys for modifiers
* added license in "About..." window

**2016-03-11 v. 2.93**

* improved modifiers selection: modifiers are now organized in list(s) and can be selected by using shortcut key


**2016-03-02 v.2.92**

* Time budget: added standard deviation values for events durations and inter-events durations
* added media file information (option) in export aggregated/tabular events outputs
* improved behavioral strings export function


**2016-02-25 v.2.9**

* added function for extracting sequences corresponding to events from media file. (See **Observations > extract events from media files** menu option.)
* improved the observation window: an observation in editing mode can now be started.
* subtitles are now created for player 1 and 2 and for all enqueued media files.
* added function for importing ethogram from text files (TSV, CSV...). See **Project window**.
* added tool for geometric measurements (distance, area and angle) in frame-by-frame mode. See **Tools > geometric measurements** menu option.

**Bugs fixed**

* fixed bug in "Edit event" function. Modifiers are no more reset to None
* fixed bug: media file name were wrong in status bar in frame-by-frame when more files were enqueued


**2016-02-09 v.2.8**

* improved checking of media files parameters (ffmpeg is now required and included in BORIS)
* improved displaying on media file information in observation window
* added spectrogram visualization in frame-by-frame mode
* comments are now exported by the "Export aggregated events" function
* added export of events in http://www.fon.hum.uva.nl/praat/manual/TextGrid.html[Praat TextGrid] format

**Bugs fixed**

* Events can now be added manually in an observation in VIEW mode
* Spectrogram is correctly visualized when media file name contains accents
* Snapshot are now correctly saved when media file name contains accents



**2015-12-22 v.2.72**

* added function for adding all media from a selected directory (on observation window)
* improved "live observation": the user can choose to delete or not the current events when live observation is restarted. Events can be added with menu option even if observation is not started.
* added function for closing ongoing events between successive videos (see observation window)

* fixed bug while adding event with "Add event" menu option during live observation not launched
* fixed bug on matplotlib backend (plot events function was not working)



**2015-12-02 v.2.7**

* added sound spectrogram visualization during observation (FFmpeg framwork required)
* added multi-editing function for events. Subject, behavior and comment fields can be edited for all the selected events.
* added time offset feature in *plot events* function
* added subjects and behaviors selection for the *export events* function
* improved control of keys in the *project* window
* preferences can no more be changed during observation


**2015-11-19 v.2.67**

* spaces contained in behavior code are replaced by underscore (_) when exported as behavioral strings (BSA is not able to recognize behaviors containing spaces)

* fix bug in "Check state events" function




**2015-11-17 v.2.66**

* added control of default value for independent variables. Must be of same type
* added function for checking the state events for each subject and modifier in the current observation. The number of state events must be odd. See **Observations > Check state events** menu option
* improved media file load

* fixed problem with matplotlib library in "Plot events" function on Mac OS X
* fixed bug when video ended
* fixed display of current media file name and current time when switching between more media
with |<< and >>| buttons


**2015-11-19 v.2.65**

* added buttons to selection window to select/deselect all subjects / all behaviors and to reverse selection
* fixed problem of media length on old project files.


**2015-11-03 v.2.64**

* fixed color issue in plot (same behaviors have now same colors)
* improved the *plot events* function:
   - added a light gray guide line
   - Point events are now plotted with symbol


**2015-10-29 v.2.63**

* fixed bug on accurate video analysis function. Video duration was not correct.

**2015-10-24 v.2.62**

* added option for allowing BORIS to check for new version (every 15 days)

* fixed bug when media files path contains accented characters on Windows

* improved search for ffmpeg executable


**2015-10-15 v.2.61**

* fixed bug in "add/edit event" function when no behavior are configured

* fixed bug on displaying video time in statusbar when video is paused




**2015-10-08 v.2.6**

* State events can now be excluded by point events

* Default time value for "Add event" menu option is now the current media position

* added "Edit observation" menu option

* fixed bug when events were added with "Add event" function (current state event(s) were not excluded)

* fixed bug when video slider was manually scrolled (media position was not updated)




**2015-09-29 v.2.55**

* added link to user guide in *help menu*

* improved media file management (when media files are not found BORIS looks for them in project directory)

* improved media accurate analysis for FPS determination for frame-by-frame mode.

* events list can be scrolled up and down when the media player is paused.

* Tracking cursor can be set above or below the current event row in events list table (see "preferences" window)

* fixed bug in "export events" function (wrong status column for events without modifiers)

* fixed bug in event double-click function when more media loaded in mediaplayer

* fixed bug in plot events function when events are not paired


**2015-09-16 v.2.5**

Major features introduced:

* introduced a tracking cursor in events table. This cursor is synchronized with media playing.

Minor features introduced:

* fixed bug in setting play rate at x1 with the (=) toolbar button

Bug fixed:

* Default play rate (x1) is printed when observation is created or opened

* Coding map was not working for event coded by double-click

* behaviors order in ethogram was wrong

* subjects order was wrong

* independent variables order was wrong

* Areas could not be modified (color, transparency) during coding map creation




**2015-09-10 v.2.4**

* bug in observation creation fixed

* Media files are now checked when selected


**2015-07-23 v.2.31**

* fixed bug on "observation" window on single media removal

**2015-07-16 v.2.3**

* Plot events with matplolib. Plot can be saved in PNG, JPG, SVG, EPS, PDF, EPS, TIFF formats

* Added a parameters panel before plot events and time budget function in oreder to select subjects and behaviors to treat. This panel allows to include/exclude modifiers and include/exclude behaviors without events.

* The % of total time changed in 'time budget' function, this value is now caculated using the total media duration (if available).

* Added VIEWER mode when media file is no more available. Events can be created, modified, deleted but not logged from keyboard.

* Media are now checked when the user add it in the 'Observation' window.


**2015-06-17 v.2.2**

* full bundle for microsoft-windows where Python 3.4, VLC, FFMPEG included


**2015-06-14**

* added sorting function for all fields in ethogram, subjects and indepedent variables tab in project window
* removed possibility to sort items manually
* added VIEW mode to visualize/modify events of an observation without the corresponding media file
* observed behaviors are now preselected in time budget and plot events functions
* fixed bug in accurate video analysis function under windows


**2015-06-05**

* separated development version ini file from stable version ini file



**2015-05-28 v.2.1**

* Video and frame-by-frame tabs in central tool box are no more enabled to user

* added media navigation keys:

For the both modes (VLC and frame-by-frame):

    Page Up key: switch to the next media
    Page Down key: switch to the previous media
    Up arrow key: jump forward in the current media
    Down arrow key: jump backward in the current media
    ESC: switch between VLC and frame-by-frame mode

Only for the frame-by-frame mode:

    Left arrow key: go to the previous frame
    Right arrow key: go to the next frame

* added CSV format for exporting events
* Time budget analysis can be exported in ODS and XLS formats
* replaced ezodf module by tablib (XLS format is now available on all platforms)
* migrated from python2.7 to python3.4




**2015-03-30 v.2.03**

* added observation information in exported events file (TSV and ODS): observation id, description, date and time offset
* fixed bug in export events in ODS format function


**2015-03-23 v.2.01**

* fixed bugs in unicode encoding in *time budget* and *visualize data* functions
* Mac OS X: fixed bug in reading video
* Mac OS X: the video can not be detached from main window.

**2015-03-17 v. 2.0**

* release of version 2.0

**2015-03-17 v.2.0 RC7**

* fixed 2 bugs in time budget function


**2015-03-12 v.2.0 RC6**

* fixed bug in frame-by-frame mode when media path contains space(s)
* fixed bug in frame-by-frame mode when media frame-by-second value is not integer


**2015-02-09 v.2.0 RC5**

* added time offset for second player
* time budget: added inter-events intervals mean
* added ODS format to "export events" function
* fixed bug in plot events function for live observation


**2015-01-13 v.2.0 RC4**

* removed time offset from media time visualization
* added qdoublespinbox to "jump to specific time" window when time format is "seconds"
* removed subtitles visualization after selecting "next" or "previous" media


**2015-01-09 v.2.0 RC3**

* fixed problem on visualization (diagram) when STATE events were not paired. 
* fixed problem when comments in event contain special characters (was not possible to reopen observation)
* improved the observations counter in Observations list window (now the counter indicate the number of filtered observations)


**2015-01-08 v. 1.64**

* fixed problem when comments in event contain special characters (was not possible to reopen observation)


**2014-12-05 v. 2.0 RC3**

* added "export aggregated events" function (tab and SQL format)
* removed automatic subtitles visualization from BORIS

**2014-11-26 v. 2.0 RC3**

* added subjects to observations filter
* added event status (START/STOP/POINT) to "export events/tabular format" function
* added possibility to export events (tabular and strings) from selected observations 
* modifiers are now in separated fields in exported events
* added options to include/exclude modifiers from subtitles


**v. 2.0 RC2 2014-11-21**

* fixed bug in deleting subject function when subject empty

**v. 2.0 RC1 (replace v. 1.7) 2014-11-18**

* added frame-by-frame mode (require the ffmpeg multimedia framework https://www.ffmpeg.org )

**v. 1.7 RC2 2014-09-12**

* fixed a bug after edit event trigger (events are no more editable in events table)

**v. 1.62 2014-09-12**

* fixed a bug after edit event trigger (events are no more editable in events table)

**v. 1.7 RC1 2014-09-04**

* added "Normal speed" button to toolbar (set play rate to 1)
* added a playback speed step value option to customize the play rate changing
* added "Snapshot" button to toolbar. The snapshot is saved on the media file path in PNG format.

**v. 1.7 RC1 2014-09-03**

* revert migration to python 2.7 due to PyInstaller incompatibility

**2014-07-24 v. 1.7 RC1**

* migration to python3
* modified subtitles function for creating subtitles for selected observations

**2014-07-18 v. 1.7 RC1**

* add function for creating subtitles for the current observation


**2014-07-17 v. 1.61**

* map creator: .boris_map extension is added to coding map file (if not present)
* map creator: added function to edit map name
* added alert when no focal subject is defined ( if option checked in Preferences window )

**2014-07-11 v. 1.6**


**2014-06-28 v 1.6 RC7**

* fixed bug in state event with coding map
* added possibility to remove modifier from coding map
* added function for checking update for Release Candidate
* added custom color and opacity for coding map region
* changed project format version (now 1.6)
* modified license GPL2->GPL3

**2014-06-26 v 1.6 RC6**

* fixed bug in setting modifier function
* fixed bug in Subject description (Empty description avoid closing project window)

**2014-06-20 v 1.6 RC5**

* fixed bug in Map creator close function (BORIS was closed)
* fixed bug in save map function in Map creator tool

**v. 2014-06-19 v 1.6 RC4**

* added dialog box when observation double clicked in observations list (Open or Edit)
* added function for importing behaviors configuration from JWatcher (Global Definition File)
* fixed old bug in media_file_information function
* fixed event interval selection (various time formats allowed)

**2014-06-09 v. 1.6 RC3**

* added modifiers editing window: modifiers are not more manually modifiable and can contain a quick key access
* fixed bug when key code various event and event with coding map is selected


**2014-05-30 v 1.521**

* fixed bug in exclusion matrix window: the excluded behaviours were manually editable.

**2014-05-27 v 1.6 RC2**

* added coding map feature
* added possibility to have more sets of modifiers for an event

**2014-05-21 v. 1.52**

* Bug fixed in time budget function (saving results)

**2014-05-16 v. 1.6 RC1**

* replaced modifier selection window with dropdown box with a window with radiobuttons
* added current modifier visualization in the panel above the media player
* added feature: a current event with modifier is now closed when the same event with different modifier is triggered
* added feature: more sets of modifiers can be defined ( alone,collaborating|  )

**2014-05-16 v. 1.51**

* fixed bug when automatically closing an event (wrong time format type)

**v. 1.5 2014-05-15**

**v. 1.5 RC2 2014-05-08**

* fixed bug in function that determine start and stop event (float -> decimal)
* fixed bug in double-click subjects list function
* fixed bug with time offset when observation was reopened

**v. 1.5 RC1 2014-05-05**

* added independent variables to project
* added the possibility to filter in the observations list window
* added statistics for each modifier to time budget 
* added track for each modifier to diagram
* added message when events are not paired during analysis
* added project file path to project window
* added list of media in "export events" function

* fixed bug on unicode key that code more events
* fixed bug on play/pause before and after code selection for multi code keys
* fixed bug on import behaviors/subjects configuration from project function
* fixed bug on observations list in the project window (media were not displayed)
* fixed bug in saving project function when project opened from command-line
* fixed bug in "jump to" function when more media enqueued
* fixed bug in "jump forward" and "jump backward" functions when more media enqueued
* fixed bug when time offset was negative

**v. 1.23 2014-01-15**

* VLC embedding Mac OS X problem: replaced set_agl by set_nsobject function
* fixed buttons position in "exclusion matrix" window
* added function to embed/detach the media player from main window (see preferences) for media player #1 and #2
* added editing of observation when media is not found

**v. 1.23 2013-12-17**

* added "Close project" function
* added a label over the media player to show focal subject, current media time etc...

**v. 1.23 2013-12-16**

* added sorting function for subjects and behaviors: sorting order can be arbitrary or alphabetical


**v. 1.22 2013-11-22**

* modified the "Export events" function: 2 formats are now available:
  * Tabular format (events from current observation)
  * Behavioral strings format for use (compatible with BSA)
* fixed bug in Mac OS X version


**v. 1.21 2013-10-15**

* added control of subject and code in event editing function:
do not more return error if the code or subject in the edited event do not more exist in the list.
* added confirmation dialog box for behavior deleting in the project editing window
* added confirmation when behaviors or subjects that are used in observation are deleted
* added a function to import behaviors and/or subjects from an other project
* added sound confirmation if key pressed (optional see Preferences to activate)
* added string format to the "export events" function


**2013-10-03 v.1.2**

* migrated media player from Qt Phonon to VLC Media Player
* added serial playing of media with cumulative time for events
* project file format changed 0 -> 1 (file extension is now .boris)
* added conversion for project file format (from .obs to .boris)
* added "check for updates" function
* live observation has now a decimal precision
* check observation id before "new observation" window closure
* removed "add second video" check box



**2013-09-30 v.0.58**

* fixed bug when creating new project


**2013-07-23 v.0.57**

* fixed bug on project initialization (behaviors already present were not deleted)
* add control of running observation before opening a project (ask user for closing observation or continuing)
* add control of unsaved project before opening a project


**2013-05-14 v.0.57**

* added automatic backup function. Interval value can be modified from the preferences window. (0 -> no backup)
* fixed bug when user Create a new project and then push Cancel button.


**2013-05-14 v 0.56**

* fixed minor bug introduced in previous version


**2013-05-13 v.0.56**

* fixed serious bug with exclusive states on multiple subjects observations (reported by Laura Ozella).

**2013-04-19 v.0.55**

* fixed bug on live observation setup


**2013-04-16 v.0.54**


* new version 0.54
* merged video and audio toolbox tabs in audio/video tab
* fixed bug during saving filename for audio observations

**2013-04-09 v.0.53**

* add "add event" function
* add "media info" with "file" utility

**2013-04-08 v. 0.521**

* removed mandatory key from subjects configuration (sent to Valentina Matteucci)

**v. 0.53**

* time budget with many observations and subjects
* diagram with many subjects


**2013-04-04 v. 0.53**

* fixed bug on function key


**2013-04-03 v. 0.53**

* modified project file format (from XML to JSON)
* add capacity to do many observations in project
* add time laps to preferences window

**2013-04-02 v.0.53**


* add preferences window

**2013-03-15 v.0.52**


* fixed error in time budget and visualization
* added table view with subjects

**2013-03-14**

* fixed bug in pausing (replaced audio pauses correctly now)
* add table widget for subject
* add save/load subjects function in project

**2013-03-11 v 0.51**

* fixed bug in leAudioFileName component name
* fixed bug in video file memorizing


**2013-03-06 v.0.5**

* fixed bug in time budget results export function
* fixed SVG diagram export

**2013-03-04 v.0.5**

* add "stop" if key pressed during current behaviour
* round time to first decimal
* add choice of subject to analyze in time budget
* replace behavior description by behavior code in diagram

**2013-02-24 v.0.5**

* export/import observations with subjects
* subject in 2nd column of observations table
* modified hh:mm:ss format in hh:mm:ss.s

**2013-02-18**

* started version 0.5 with subject

**2013-02-12 v.0.11**

* add "Data visualization" menu option: observations can be plotted in SVG format
* add more functions to time budget: behaviours are now excluded when calculating the time budget 

**2013-02-11 v.0.10**

* time offset can now be negative
* time offset is saved in project file

**2013-01-26 v.0.10**

* modified video synchronisation by clicking on observations:
  * Now the time offset is subtracted.
  * The second video/audio is also synchronized

**2013-01-25 v.0.09**

* tested observation project made with v7 -> OK
* tested import of ethogram exported with v7 -> OK
* changed program name to **BORIS**
* fixed export/import configuration of observations
* fixed the playing with modified speed at end of video (now the video stops playing)
* changed the default time format to hh:mm:ss

**2013-01-24 v.0.08**

* add control of options "replace audio" and "second video". Now they are exclusive.
* time offset can be set in hh:mm:ss format
* added a label in status bar for displaying the time offset

**2013-01-23**

* reorganized the whole directory
* add obs extension when project saved without extention when *.obs filter is active
* edit project: check replace audio check box if necessary
* edit project: check second video check box if necessary



