import sys
from PySide6.QtWidgets import QApplication
from uimain import MainWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    app.setOrganizationName("FreeWili")
    app.setOrganizationDomain("freewili.com")
    app.setApplicationName("FreeWiliUpdater")   

    main_widget = MainWidget()
    main_widget.show()

    sys.exit(app.exec())

