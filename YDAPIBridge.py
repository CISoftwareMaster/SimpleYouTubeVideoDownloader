import json
from enum import Enum
from PyQt5.Qt import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *


class YDAPIRequestType(Enum):
    NoRequest = 0
    VideoInfo = 1
    ActualVideo = 2


# this is our YouTube downloader bridge
class YDAPIBridge(QObject):
    # progress bar signals
    progressMaxChanged = pyqtSignal(int)
    progressChanged = pyqtSignal(int)
    downloadProgressChanged = pyqtSignal(int, int)

    # download signals
    downloadFailed = pyqtSignal(str)
    downloadJSONFinished = pyqtSignal(dict)
    downloadFileFinished = pyqtSignal(bytes)

    # command signals
    cancelRequests = pyqtSignal()

    def __init__(self):
        # initialise QObject
        super().__init__()

        # initialise our network manager
        self.networkManager = QNetworkAccessManager()

        # reference to our current network request
        self.currentRequest = None

        # last request type
        self.lastType = YDAPIRequestType.NoRequest

        # are we currently processing any requests?
        self.active = False

        # connect our download finished signal
        self.networkManager.finished.connect(self.downloadFinished)

    # download finished
    @pyqtSlot(QNetworkReply)
    def downloadFinished(self, reply):
        if reply is not None:
            # reset active flag
            self.active = False

            # get status code
            statusCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

            # alert the user if we get an error
            if reply.error():
                self.downloadFailed.emit(reply.errorString())

            # check for redirects
            elif statusCode >= 301 and statusCode <= 308:
                # get redirect URL
                redirectURL = f"http:{reply.attribute(QNetworkRequest.RedirectionTargetAttribute).toString()}"

                # re-send our request (but this time, to the redirection target)
                self.sendRequest(redirectURL, self.lastType)

            else:
                data = reply.readAll()

                # check request type
                if self.lastType == YDAPIRequestType.VideoInfo:
                    # json-ify the data
                    try:
                        data = json.loads(bytes(data).decode("utf-8"))
                    except:
                        # welp, that didn't go so well...
                        self.downloadFailed.emit("Video information download failed!")
                        return

                    # emit our download finished signal
                    self.downloadJSONFinished.emit(data)

                elif self.lastType == YDAPIRequestType.ActualVideo:
                    self.downloadFileFinished.emit(bytes(data))

    # download progress
    def downloadProgress(self, value, max_):
        self.progressMaxChanged.emit(max_)
        self.progressChanged.emit(value)
        self.downloadProgressChanged.emit(value, max_)

    # send a network request (with an inbuilt kill-switch)
    def sendRequest(self, url, type_: YDAPIRequestType):
        # stop active requests
        if self.currentRequest is not None:
            # send our kill signal
            self.cancelRequests.emit()

            # delete our current request
            self.currentRequest.deleteLater()

        # send a new request
        request = QNetworkRequest(QUrl(url))
        self.currentRequest = self.networkManager.get(request)

        # set our last request type
        self.lastType = type_

        # set active flag
        self.active = True

        # connect our kill command signal
        self.cancelRequests.connect(self.currentRequest.abort)
        # connect our progress update slot
        self.currentRequest.downloadProgress.connect(self.downloadProgress)

    # get YouTube video info from saveoffline.com
    def getVideoInformation(self, url):
        self.sendRequest(self.prepareURL(url), YDAPIRequestType.VideoInfo)

    # API URL
    def prepareURL(self, url):
        return f"https://www.saveoffline.com/process/?url={url}?type=json"

    # stop any current activities
    def stopAll(self):
        # send our kill command
        self.cancelRequests.emit()
