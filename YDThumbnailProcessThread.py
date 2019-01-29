from urllib.request import urlopen
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class YDThumbnailProcessThread(QThread):
    thumbnailReady = pyqtSignal(QPixmap)

    def __init__(self):
        # initialise QThread
        super().__init__()

        # target URL
        self.targetUrl = None
        self.active = False

    def begin(self, url):
        if not self.active:
            self.targetUrl = url

            # start this thread
            self.start(QThread.HighPriority)

    def run(self):
        # this is where our data would be loaded
        image =  QPixmap()

        # open the target URL
        try:
            with urlopen(self.targetUrl) as imageDoc:
                # download the thumbnail image to memory
                image.loadFromData(imageDoc.read())
                imageDoc.close()
        except:
            print("Failed loading thumbnail image!")
            self.exit(1)
            return

        # thumbnail loaded!
        self.thumbnailReady.emit(image)

        # end of process
        self.exit(0)
