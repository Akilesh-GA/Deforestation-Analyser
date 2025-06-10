from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QProgressBar, QPushButton
from PyQt6.QtGui import QFont, QPainter, QColor
from PyQt6.QtCore import Qt
import sys

class DeforestationAnalysis(QWidget):
    def __init__(self, confidence, deforestation_score, Location, Date):
        super().__init__()
        self.initUI(confidence, deforestation_score, Location, Date)


    def initUI(self , confidence , deforestation_score , Location , Date):
        self.setWindowTitle("Deforestation Analysis Report")
        self.setGeometry(200, 200, 400, 400)

        layout = QVBoxLayout()

        # Title Label
        title_label = QLabel("🌲 Deforestation Analysis Report 🌲")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Confidence Label
        self.confidence = confidence * 100 # Confidence in %
        confidence_label = QLabel(f"🔍 Confidence: {self.confidence}%")
        confidence_label.setFont(QFont("Arial", 11))
        layout.addWidget(confidence_label)

        # Confidence Progress Bar
        self.confidence_bar = QProgressBar(self)
        self.confidence_bar.setValue(int(self.confidence))
        self.confidence_bar.setTextVisible(True)
        layout.addWidget(self.confidence_bar)

        # Deforestation Score Gauge
        self.deforestation_score = deforestation_score # Example score
        self.gauge_label = QLabel(self)
        self.gauge_label.setFixedSize(150, 150)
        layout.addWidget(self.gauge_label)

        # Location and Time
        location_label = QLabel(f"📍 Location: {Location}")
        location_label.setFont(QFont("Arial", 11))
        layout.addWidget(location_label)

        date_label = QLabel(f"Date: {Date}")
        date_label.setFont(QFont("Arial", 11))
        layout.addWidget(date_label)

        # File Save Location
        file_label = QLabel("📂 Results saved to: analysis_result_1741582220.txt")
        file_label.setFont(QFont("Arial", 11))
        layout.addWidget(file_label)

        # self.oxygenLevel = QLabel(f'Oxygen Level { confidence / 100 } ')
        # self.oxygenLevel.setFont(QFont("Arial" , 11))
        # layout.addWidget(self.oxygenLevel)
       
        if self.confidence >= 50:
             self.Deforest_Display = QLabel(f'🚩Resule : Deforest')
             self.Deforest_Display.setFont(QFont("Arial" , 11))
             layout.addWidget(self.Deforest_Display)
        else:
            self.Deforest_Display = QLabel(f'🌲Resule : Not Deforest')
            self.Deforest_Display.setFont(QFont("Arial" , 11))
            layout.addWidget(self.Deforest_Display)\
        


        # OK Button
        btn = QPushButton("OK")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)

        self.setLayout(layout)

    def paintEvent(self, event):
        """ Custom paint event for drawing a circular gauge """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.gauge_label.geometry()
        center_x, center_y = rect.center().x(), rect.center().y()

        radius = 60
        start_angle = 90 * 16  # Qt uses 1/16th of a degree
        span_angle = int(-360 * self.deforestation_score * 16)  # Full circle for max score

        # Draw the background circle
        painter.setBrush(QColor(230, 230, 230))
        painter.drawEllipse(center_x - radius, center_y - radius, 2 * radius, 2 * radius)

        # Draw the deforestation score indicator
        painter.setBrush(QColor(255, 69, 0))  # Red for impact
        painter.drawPie(center_x - radius, center_y - radius, 2 * radius, 2 * radius, start_angle, span_angle)

        # Draw the center circle
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(center_x - 20, center_y - 20, 40, 40)

        # Draw text
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(center_x - 20, center_y + 5, f"{self.deforestation_score:.2f}")

# Run Application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeforestationAnalysis()
    window.show()
    sys.exit(app.exec())
