import sys
import subprocess
from PyQt5.QtCore import *
from PyQt5.Qt import *
from YDMainWindow import YDMainWindow


if __name__ == "__main__":
    # initialise our Qt app
    app = QApplication(sys.argv)

    # initialise our window
    window = YDMainWindow()
    window.show()

    # add KDE blur effect
    subprocess.run(["xprop","-f", "_KDE_NET_WM_BLUR_BEHIND_REGION", "32c",
                    "-set", "_KDE_NET_WM_BLUR_BEHIND_REGION", "0", "-name",
                    "YouTube Video Downloader"])

    # execute our app
    sys.exit(app.exec_())
