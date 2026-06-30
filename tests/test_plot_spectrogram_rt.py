import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import parselmouth
from matplotlib import pyplot
from PySide6.QtWidgets import QApplication

from boris import config as cfg
from boris.plot_spectrogram_rt import (
    PRAAT_LIKE_COLOR_MAP,
    Plot_spectrogram_RT,
    _apply_pre_emphasis,
    _lookup_table_from_colormap,
    _praat_spectrogram_parameters,
    _spectrogram_levels,
)


def test_praat_spectrogram_parameters_are_not_derived_from_nfft_overlap():
    window_length, time_step, frequency_step, window_shape = _praat_spectrogram_parameters()

    assert window_length == 0.005
    assert time_step == 0.002
    assert frequency_step == 20.0
    assert window_shape == parselmouth.SpectralAnalysisWindowShape.GAUSSIAN


def test_spectrogram_levels_use_parselmouth_example_dynamic_range():
    spectrogram = parselmouth.Sound("tests/files/test.wav").to_spectrogram()
    levels = _spectrogram_levels(10 * np.log10(spectrogram.values + 1e-20))

    assert levels[1] - levels[0] == 70.0


def test_lookup_table_uses_matplotlib_colormaps_for_pyqtgraph():
    lookup_table = _lookup_table_from_colormap(pyplot.get_cmap(PRAAT_LIKE_COLOR_MAP))

    assert lookup_table.shape == (256, 3)
    assert lookup_table.dtype == np.ubyte
    assert not np.array_equal(lookup_table[0], lookup_table[-1])


def test_pre_emphasis_changes_sound_chunk_values():
    sound = parselmouth.Sound("tests/files/test.wav").extract_part(from_time=0, to_time=1, preserve_times=False)
    original_values = sound.values.copy()

    emphasized = _apply_pre_emphasis(sound, True)

    assert emphasized is sound
    assert not np.allclose(original_values, emphasized.values)


def test_plot_spectrogram_uses_parselmouth_sound():
    QApplication.instance() or QApplication([])
    widget = Plot_spectrogram_RT()

    try:
        result = widget.load_wav("tests/files/test.wav")
        f, t_rel, power = widget._compute_spectrogram(
            start_time=0,
            end_time=1,
            maximum_frequency=5000,
        )
    finally:
        widget.close()

    assert "error" not in result
    assert result["frame_rate"] == 44100
    assert result["media_length"] > 60
    assert f.size > 0
    assert t_rel.size > 0
    assert power.shape == (f.size, t_rel.size)


def test_plot_spectrogram_pre_emphasis_flag_changes_power_values():
    QApplication.instance() or QApplication([])
    widget = Plot_spectrogram_RT()

    try:
        result = widget.load_wav("tests/files/test.wav")
        widget.config_param[cfg.SPECTROGRAM_PRE_EMPHASIZE] = False
        _, _, power_without_pre_emphasis = widget._compute_spectrogram(
            start_time=0,
            end_time=1,
            maximum_frequency=5000,
        )
        widget.config_param[cfg.SPECTROGRAM_PRE_EMPHASIZE] = True
        _, _, power_with_pre_emphasis = widget._compute_spectrogram(
            start_time=0,
            end_time=1,
            maximum_frequency=5000,
        )
    finally:
        widget.close()

    assert "error" not in result
    assert power_without_pre_emphasis.shape == power_with_pre_emphasis.shape
    assert not np.allclose(power_without_pre_emphasis, power_with_pre_emphasis)
