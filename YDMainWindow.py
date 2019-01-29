import io
import re
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from YDThumbnailProcessThread import YDThumbnailProcessThread
from YDAPIBridge import *


# table view data name(s)
DataUrl = 0x9000
DataSuggestedFilename = 0x9001

# compile our label extraction patterns
typePattern = re.compile("(audio|video)")
qualityPattern = re.compile("[0-9]+p|[0-9]+ ?kbps")
extensionPattern = re.compile("(webm|m4a|mp4|3gp)")


# our main window
class YDMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # set minimum dimensions
        self.setMinimumSize(640, 720)
        self.setWindowTitle("YouTube Video Downloader")

        # get background colour
        bc = self.palette().brush(QPalette.Background).color()

        # make the window translucent (because, why not?)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # set new brush
        self.setStyleSheet(f"background: rgba({bc.red()}, {bc.green()}, {bc.blue()}, 0.65)")

        # initialise view + layout
        view = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # initialise our widgets
        self.urlBar = QLineEdit()
        self.urlBar.setPlaceholderText("YouTube video URL goes here")

        # download button
        self.downloadStart = QPushButton("Get")
        self.resetButton = QPushButton("Reset")

        # make the URL bar and download button transparent
        self.urlBar.setStyleSheet(f"background: rgba({bc.red()}, {bc.green()}, {bc.blue()}, 0.25)")
        self.downloadStart.setStyleSheet(f"background: rgba({bc.red()}, {bc.green()}, {bc.blue()}, 0.25)")
        self.resetButton.setStyleSheet(f"background: rgba({bc.red()}, {bc.green()}, {bc.blue()}, 0.25)")

        # hide reset button
        self.resetButton.hide()

        # urlBar + download button view + layout
        uView = QWidget()
        uLayout = QHBoxLayout()
        uLayout.setContentsMargins(0, 0, 0, 0)

        # create urlBar + download button view
        uLayout.addWidget(self.urlBar)
        uLayout.addWidget(self.downloadStart)
        uLayout.addWidget(self.resetButton)
        uView.setLayout(uLayout)

        # initialise our thumbnail view + layout
        tView = QWidget()
        tlayout = QVBoxLayout()
        tlayout.setContentsMargins(0, 0, 0, 0)

        # our thumbnail labels
        self.thumbnail = QLabel("")
        self.thumbnailTitle = QLabel("")
        self.thumbnailTitle.setWordWrap(True)

        # they have transparent backgrounds
        self.thumbnail.setStyleSheet("background: transparent")
        self.thumbnailTitle.setStyleSheet("background: transparent")

        # set alignment
        self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnailTitle.setAlignment(Qt.AlignCenter)

        # set font for thumbnail title
        font = self.thumbnailTitle.font()
        font.setPointSize(18)
        font.setBold(True)
        self.thumbnailTitle.setFont(font)

        # set max thumbnail dimensions
        self.thumbnail.setMaximumHeight(480)

        # create our thumbnail widgets
        tlayout.addWidget(self.thumbnail)
        tlayout.addWidget(self.thumbnailTitle)
        tView.setLayout(tlayout)

        # progress bar view + layout
        self.pView = QWidget()
        pLayout = QVBoxLayout()
        pLayout.setContentsMargins(0, 0, 0, 0)

        # progress bar label
        self.progressLabel = QLabel("Done...")
        self.progressBar = QProgressBar()

        # create progress bar widget
        pLayout.addWidget(self.progressLabel)
        pLayout.addWidget(self.progressBar)
        self.pView.setLayout(pLayout)

        # create our options list
        self.options = QTableWidget()

        # set up table view
        self.options.verticalHeader().hide()
        self.options.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.options.setSelectionBehavior(QTableWidget.SelectRows)
        self.options.setSelectionMode(QTableWidget.SingleSelection)
        self.options.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

        # insert widgets into view
        layout.addWidget(tView)
        layout.addWidget(self.pView)
        layout.addItem(QSpacerItem(0, 4))
        layout.addWidget(uView)
        layout.addWidget(self.options)

        # make everything else opaque
        self.pView.setStyleSheet(f"background: rgb({bc.red()}, {bc.green()}, {bc.blue()})")
        self.options.setStyleSheet(f"background: rgb({bc.red()}, {bc.green()}, {bc.blue()})")

        # hide progress bar view
        self.pView.hide()

        # finalise
        view.setLayout(layout)
        self.setCentralWidget(view)

        # initialise table view with an empty set
        self.populateTableView()

        # initialise our API bridge
        self.apiBridge = YDAPIBridge()

        # initialise our thumbnail processing thread
        self.thumbnailProcessor = YDThumbnailProcessThread()

        # connect our signals
        self.apiBridge.progressMaxChanged.connect(self.progressBar.setMaximum)
        self.apiBridge.progressChanged.connect(self.progressBar.setValue)
        self.apiBridge.downloadJSONFinished.connect(self.populateTableView)
        self.apiBridge.downloadFileFinished.connect(self.saveDownloadedVideo)
        self.apiBridge.downloadFailed.connect(self.showErrorMsg)
        self.apiBridge.downloadProgressChanged.connect(self.downloadProgressChanged)

        self.thumbnailProcessor.thumbnailReady.connect(self.thumbnail.setPixmap)
        self.downloadStart.clicked.connect(self.get)
        self.resetButton.clicked.connect(self.reset)

        # save file dialogue
        self.downloadDialogue = QFileDialog()
        self.downloadDialogue.setAcceptMode(QFileDialog.AcceptSave)
        self.downloadDialogue.setFileMode(QFileDialog.AnyFile)
        self.downloadDialogue.setDirectory(QDir.current())

        # download filename
        self.downloadFilename = ""

        # cached download file
        self.downloadedFile = None

    @pyqtSlot()
    def reset(self):
        x = QMessageBox.warning(self, "Warning", "This would cancel any active downloads!", QMessageBox.Ok | QMessageBox.Cancel)

        if x == QMessageBox.Ok:
            # reset table view and download button
            self.populateTableView()
            self.downloadStart.setText("Get")

            # reset thumbnail
            self.thumbnail.setPixmap(QPixmap())
            self.thumbnailTitle.setText("")

            # reset progress bar
            self.progressLabel.setText("Done...")
            self.progressBar.setValue(0)
            self.pView.hide()

            # reset any cached downloaded file references
            self.downloadedFile = None

            # reset download filename
            self.downloadFilename = ""

            # kill any running activities
            self.apiBridge.stopAll()

            # force re-enable the download button
            self.downloadStart.setEnabled(True)

            # reset the reset button
            self.resetButton.hide()
            self.resetButton.setText("Reset")

    @pyqtSlot(dict)
    def populateTableView(self, info=None):
        # reset items
        self.options.setRowCount(0)
        self.options.setColumnCount(3)

        # set column labels
        self.options.setHorizontalHeaderLabels(["Type", "Quality", "File Extension"])

        # set content (if available)
        if info is not None:
            # update thumbnail info
            self.thumbnailTitle.setText(info["title"])

            # load thumbnail image
            self.thumbnailProcessor.begin(info["thumbnail"])

            # load items
            for item in info["urls"]:
                labels = item["label"]

                # extract information from our label
                try:
                    itemExtension = extensionPattern.findall(labels)[0]
                except:
                    itemExtension = "mp4"

                try:
                    itemType = typePattern.findall(labels)[0]

                    # capitalise it
                    itemType = f"{itemType[0].upper()}{itemType[1::]}"
                except:
                    itemType = "Video + Audio"

                try:
                    itemQuality = qualityPattern.findall(labels)[0]
                except:
                    itemQuality = "Unknown"

                # set row info
                typeColumn = QTableWidgetItem(itemType)
                typeColumn.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                typeColumn.setData(DataUrl, item["id"])

                qualityColumn = QTableWidgetItem(itemQuality)
                qualityColumn.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                qualityColumn.setData(DataUrl, item["id"])

                extensionColumn = QTableWidgetItem(itemExtension)
                extensionColumn.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                extensionColumn.setData(DataUrl, item["id"])

                # create our suggested filename
                suggestedFilename = f"{info['title']}-{itemQuality}.{itemExtension}"

                # set suggested filename data
                typeColumn.setData(DataSuggestedFilename, suggestedFilename)
                qualityColumn.setData(DataSuggestedFilename, suggestedFilename)
                extensionColumn.setData(DataSuggestedFilename, suggestedFilename)

                # insert new row
                targetRow = self.options.rowCount()
                self.options.insertRow(targetRow)
                self.options.setItem(targetRow, 0, typeColumn)
                self.options.setItem(targetRow, 1, qualityColumn)
                self.options.setItem(targetRow, 2, extensionColumn)

            # flip download button text
            self.progressLabel.setText("Done...")
            self.downloadStart.setText("Download")
            self.resetButton.show()

            # hide progress bar view
            self.pView.hide()

    @pyqtSlot()
    def get(self):
        if self.downloadStart.text() == "Get":
            videoURL = self.urlBar.text()

            # send a get video information request to our API Bridge
            self.apiBridge.getVideoInformation(videoURL)

            # show progress bar view
            self.progressLabel.setText("Getting video information...")
            self.pView.show()

        elif self.downloadStart.text() == "Download":
            # only allow downloading if we actually have a selection
            if self.options.currentRow() != -1:
                # set suggested filename
                suggestedFilename = self.options.currentItem().data(DataSuggestedFilename)

                # open our download path dialog
                self.downloadFilename = self.downloadDialogue.getSaveFileName(
                    self, "Download this where?", suggestedFilename,
                    "Video Files (*.mp4, *.m4a, *.webm, *.3gp)")

                # check our downloaded filename
                if self.downloadFilename[0] != '':
                    self.downloadFilename = self.downloadFilename[0]

                    # start downloading the video file
                    if self.downloadedFile is None:
                        # update progress label
                        self.progressLabel.setText("Downloading video...")
                        self.pView.show()

                        # get the target video URL
                        videoUrl = self.options.currentItem().data(DataUrl)
                        print(videoUrl)

                        # start downloading the video file
                        self.apiBridge.sendRequest(videoUrl, YDAPIRequestType.ActualVideo)

                        # disable the download button
                        self.downloadStart.setEnabled(False)

                        # the reset button becomes "abort"
                        self.resetButton.setText("Cancel")

                    # we already have a cached video file, re-try saving it at the new location
                    else:
                        self.saveDownloadedVideo(self.downloadedFile)

    @pyqtSlot(bytes)
    def saveDownloadedVideo(self, videoData):
        # start saving the video file
        try:
            with io.open(self.downloadFilename, "wb") as videoFile:
                videoFile.write(videoData)
                videoFile.close()
        except:
            # there was an error, cache our result then try again
            self.downloadedFile = videoData
            self.downloadDialogue.show()
            return

        # un-set cached download reference
        self.downloadedFile = None

        # hide progress bar
        self.progressBar.setValue(0)
        self.pView.hide()

        # re-enable the download button
        self.downloadStart.setEnabled(True)
        # reset the reset button
        self.resetButton.setText("Reset")

    @pyqtSlot(str)
    def showErrorMsg(self, msg):
        QMessageBox.warning(self, "Error!", msg)

    @pyqtSlot(int, int)
    def downloadProgressChanged(self, a, b):
        self.progressLabel.setText(f"{a/1024:,.2f} KB / {b/1024:,.2f} KB")
