from .view_df_ui import Ui_Form
from PySide6.QtWidgets import QWidget, QFileDialog
from PySide6.QtCore import Qt, QAbstractTableModel

from . import config as cfg
from pathlib import Path
from . import dialog

try:
    import pyreadr

    flag_pyreadr_loaded = True
except ModuleNotFoundError:
    flag_pyreadr_loaded = False


class DataFrameModel(QAbstractTableModel):
    def __init__(self, dataframe):
        super().__init__()
        self._dataframe = dataframe

    def rowCount(self, parent=None):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None):
        return self._dataframe.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self._dataframe.iat[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._dataframe.columns[section]
            elif orientation == Qt.Vertical:
                return self._dataframe.index[section]
        return None


class View_df(QWidget, Ui_Form):
    def __init__(self, plugin_name: str, plugin_version: str, df, parent=None):
        super().__init__()
        self.plugin_name = plugin_name
        self.df = df

        self.setupUi(self)
        self.lb_plugin_info.setText(f"{plugin_name} v. {plugin_version}")
        self.setWindowTitle(f"{plugin_name} v. {plugin_version}")

        # print(f"{self.df=}")

        self.pb_close.clicked.connect(self.close)
        self.pb_save.clicked.connect(self.save)

        model = DataFrameModel(self.df)
        self.tv_df.setModel(model)

    def save(self):
        file_formats = (
            cfg.TSV,
            cfg.CSV,
            cfg.ODS,
            cfg.XLSX,
            # cfg.XLS,
            cfg.HTML,
            # cfg.TBS,
            cfg.PANDAS_DF,
            cfg.RDS,
        )

        file_dialog_options = QFileDialog.Options()
        file_dialog_options |= QFileDialog.DontConfirmOverwrite

        file_name, filter_ = QFileDialog().getSaveFileName(
            None, f"Save {self.plugin_name}", "", ";;".join(file_formats), options=file_dialog_options
        )
        if not file_name:
            return

        outputFormat = cfg.FILE_NAME_SUFFIX[filter_]
        if Path(file_name).suffix != "." + outputFormat:
            file_name = f"{file_name}.{outputFormat}"
            if Path(file_name).exists():
                if (
                    dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE])
                    == cfg.CANCEL
                ):
                    return

        if filter_ == cfg.TSV:
            self.df.to_csv(file_name, sep="\t", index=False)
        if filter_ == cfg.CSV:
            self.df.to_csv(file_name, sep=";", index=False)
        if filter_ == cfg.XLSX:
            self.df.to_excel(file_name, index=False)
        if filter_ == cfg.ODS:
            self.df.to_excel(file_name, index=False, engine="odf")
        if filter_ == cfg.HTML:
            self.df.to_html(file_name, index=False)
        if filter_ == cfg.PANDAS_DF:
            self.df.to_pickle(file_name)

        if filter_ == cfg.RDS and flag_pyreadr_loaded:
            pyreadr.write_rds(file_name, self.df)
