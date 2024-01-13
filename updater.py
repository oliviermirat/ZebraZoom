import atexit
import os
import sys
import zipfile
from io import BytesIO

from PyQt5.QtCore import Qt, QEventLoop, QStandardPaths, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


class _Application(QApplication):
    def __init__(self, args):
        super().__init__(args)
        if sys.platform.startswith('win'):  # qt5 uses deprecated windows API to determine the system font, this works around that issuue
            self.setFont(QApplication.font("QMessageBox"))


class _UpdaterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumWidth(300)
        layout = QVBoxLayout()
        titleLabel = QLabel('Updating ZebraZoom...')
        titleLabel.setFont(QFont('Times New Roman', 16))
        layout.addWidget(titleLabel, alignment=Qt.AlignmentFlag.AlignCenter)
        progressLabel = QLabel()
        layout.addWidget(progressLabel)
        progressBar = QProgressBar()
        layout.addWidget(progressBar)
        self.updateState = lambda state, total, text, showBtn=False: progressBar.setMaximum(total) or progressBar.setValue(state) or progressLabel.setText(text) or cancelDownloadBtn.setVisible(showBtn)
        cancelDownloadBtn = QPushButton("Cancel download")
        cancelDownloadBtn.clicked.connect(lambda: sys.exit(0))
        layout.addWidget(cancelDownloadBtn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setLayout(layout)


class _ZipFile(zipfile.ZipFile):  # this is required to work around a bug in ZipFile (https://github.com/python/cpython/issues/59999)
    def _extract_member(self, member, targetpath, pwd):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)
        path = super()._extract_member(member, targetpath, pwd)
        if member.external_attr > 0xffff:
            os.chmod(path, member.external_attr >> 16)
        return path


if __name__ == '__main__' and getattr(sys, 'frozen', False):  # running an installed executable
    zebrazoomExecutable = 'ZebraZoom.exe' if sys.platform.startswith('win') else 'ZebraZoomApp' if sys.platform == 'darwin' else "ZebraZoom"
    atexit.register(os.execl, zebrazoomExecutable, zebrazoomExecutable)
    installationFolder = os.path.dirname(os.path.dirname(sys.executable))
    legacyFormat = os.path.exists(os.path.join(installationFolder, zebrazoomExecutable))
    atexit.register(os.chdir, installationFolder if legacyFormat else os.path.dirname(installationFolder))

    app = _Application(sys.argv)
    loop = QEventLoop()
    networkManager = QNetworkAccessManager()
    if legacyFormat:
        assetName = f"ZebraZoom-{'update-Windows' if sys.platform.startswith('win') else 'update-macOS' if sys.platform == 'darwin' else 'Linux'}.zip"
    else:
        assetName = f"ZebraZoom-{'Windows' if sys.platform.startswith('win') else 'macOS' if sys.platform == 'darwin' else 'Linux'}.zip"
    window = _UpdaterWindow()
    window.show()
    rect = window.geometry()
    rect.moveCenter(window.screen().availableGeometry().center())
    window.setGeometry(rect)
    downloadRequest = QNetworkRequest(QUrl(f'https://github.com/oliviermirat/ZebraZoom/releases/latest/download/{assetName}'))
    downloadRequest.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
    download = networkManager.get(downloadRequest)

    def downloadProgress(bytesReceived, bytesTotal):
        if bytesTotal < 0:
            return
        window.updateState(bytesReceived, bytesTotal, 'Downloading update...', showBtn=True)
    download.downloadProgress.connect(downloadProgress)
    download.finished.connect(lambda: loop.exit())
    loop.exec()
    if download.error() != QNetworkReply.NetworkError.NoError:
        QMessageBox.critical(window, "Download failed", "Could not download the update, please try again or update manually.")
        sys.exit(0)

    try:
        with open(os.path.join(installationFolder, 'installedFiles.txt')) as f:
            installedFiles = f.read().splitlines()
        if not legacyFormat:
            installedFiles.append(os.path.join('..', zebrazoomExecutable))
    except EnvironmentError:
        QMessageBox.critical(window, "Error deleting old files", "Could not delete some of the old files. Installation might have been damaged, please reinstall ZebraZoom manually.")
        sys.exit(0)

    dataInDocuments = os.path.exists(os.path.join(installationFolder, 'Uninstall.exe'))
    documentsFolder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    processedSize = 0
    totalSize = len(installedFiles)
    try:
        for fname in installedFiles:
            if fname.startswith('updater'):
                continue
            if dataInDocuments and any(fname.startswith(folder) for folder in ('zebrazoom\configuration', 'zebrazoom\dataAnalysis', 'zebrazoom\ZZoutput')):
                path = os.path.join(documentsFolder, 'ZebraZoom', fname.lstrip('zebrazoom\\'))
            else:
                path = os.path.join(installationFolder, fname)
            window.updateState(processedSize, totalSize, 'Removing old files...')
            processedSize += 1
            if os.path.isdir(path):
                try:
                    os.rmdir(path)
                except OSError:
                    continue  # directory is not empty; skip it
            elif os.path.exists(path):
                os.remove(path)
    except EnvironmentError:
        QMessageBox.critical(window, "Error deleting old files", "Could not delete some of the old files. Installation might have been damaged, please reinstall ZebraZoom manually.")
        sys.exit(0)

    try:
        with _ZipFile(BytesIO(download.readAll()), 'r') as archive:
            totalSize = sum(info.file_size for info in archive.infolist())
            processedSize = 0
            window.updateState(processedSize, totalSize, 'Extracting new files...')
            for info in archive.infolist():
                extractToFolder = installationFolder if legacyFormat else os.path.dirname(installationFolder)
                if 'updater/updater' in info.filename:
                    info.filename += '.new'
                elif dataInDocuments and any(info.filename.startswith(folder) for folder in ('zebrazoom/configuration', 'zebrazoom/dataAnalysis', 'zebrazoom/ZZoutput')):
                    info.filename = info.filename.lstrip('zebrazoom/')
                    extractToFolder = os.path.join(documentsFolder, 'ZebraZoom')
                archive.extract(info, extractToFolder)
                processedSize += info.file_size
                window.updateState(processedSize, totalSize, 'Extracting new files...')
    except:  # we really don't care what goes wrong here
        QMessageBox.critical(window, "Error extracting new files", "Could not extract some files. Installation might have been damaged, please reinstall ZebraZoom manually.")
