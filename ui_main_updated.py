import sys
import time
import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QLineEdit, QPushButton, QLabel, QProgressBar, QMessageBox
)
from Rep import DeforestationAnalysis
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QTimer, QUrl, Qt
from PyQt6.QtGui import QIcon, QFont
from ethereum_integration import EthereumBlockchain 
from forest2 import get_forest_data
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QWidget, QLabel, QFileDialog
import pandas as pd

import requests
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QLineEdit, QMessageBox

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from datetime import datetime
from com import get_deforestation_data
from deforest1 import ForestMonitoringApp  # Make sure 1.py is renamed to deforest1.py




class MainWindow(QMainWindow , EthereumBlockchain):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deforestation Analysis - 3D Map Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Current location coordinates
        self.current_latitude = 0.0
        self.current_longitude = 0.0
        
        # Status indicators
        self.is_loading = False
        self.is_analyzing = False
        
        # Initialize Ethereum blockchain
        try:
            self.blockchain = EthereumBlockchain()
            print("The Location Got Success")
            print("Blockchain integration initialized")
        except Exception as e:
            self.blockchain = None
            print(f"Failed to initialize blockchain: {str(e)}")

        # Create a web view widget
        self.browser = QWebEngineView()
        self.browser.setHtml(self.get_html())  # Load CesiumJS map
        self.browser.loadFinished.connect(self.on_page_loaded)

        # Input field for country name
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter country name...")
        self.input_field.returnPressed.connect(self.navigate_to_country)
        
        # Button to navigate to the country
        self.go_button = QPushButton("Go")
        self.go_button.clicked.connect(self.navigate_to_country)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Coordinates display
        self.coords_label = QLabel("Lat: 0.0°, Lon: 0.0°")
        self.coords_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Button to capture screenshot
        self.capture_button = QPushButton("Capture Screenshot & Analyze")
        self.capture_button.clicked.connect(self.capture_screenshot)
        self.capture_button.setEnabled(False)  # Disabled until map loads
        
        # Add button to plot forest locations
        self.plot_forests_button = QPushButton("Plot Indian Forests")
        self.plot_forests_button.clicked.connect(self.plot_indian_forests)
        self.plot_forests_button.setEnabled(False)  # Disabled until map loads
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Search area
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Location:"))
        search_layout.addWidget(self.input_field, 1)
        search_layout.addWidget(self.go_button)
        main_layout.addLayout(search_layout)
        
        # Info area
        info_layout = QHBoxLayout()
        info_layout.addWidget(self.coords_label, 1)
        info_layout.addWidget(self.status_label)
        main_layout.addLayout(info_layout)
        
        # Action area
        action_layout = QHBoxLayout()
        action_layout.addWidget(self.capture_button)
        action_layout.addWidget(self.plot_forests_button)
        action_layout.addWidget(self.progress_bar)
        main_layout.addLayout(action_layout)
        
        # Map view
        main_layout.addWidget(self.browser, 1)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        # Add this to your __init__ method in the MainWindow class, right after the plot_forests_button
        self.poaching_detection_button = QPushButton("Poaching Detection")
        self.poaching_detection_button.clicked.connect(self.open_poaching_window)
        action_layout.addWidget(self.poaching_detection_button)

    def get_html(self):
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <script src="https://cesium.com/downloads/cesiumjs/releases/1.99/Build/Cesium/Cesium.js"></script>
            <link href="https://cesium.com/downloads/cesiumjs/releases/1.99/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
            <style>
                html, body, #cesiumContainer { width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; }
            </style>
        </head>
        <body>
            <div id="cesiumContainer"></div>
            <script>
                // Initialize the Cesium Viewer
                Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI4ZmYwM2JiMS1jZThhLTQzZDUtOTliYS1lMzdiNzJkMjQ4YTAiLCJpZCI6Mjc4MzgzLCJpYXQiOjE3NDAzMDgxMTh9.08DTTHzrWKqlOLwadyXDOfi_cAaJe3Y-tRoZpoIMEKw';
                
                const viewer = new Cesium.Viewer('cesiumContainer', {
                    imageryProvider: new Cesium.ArcGisMapServerImageryProvider({
                        url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer'
                    }),
                    baseLayerPicker: true,
                    geocoder: false,
                    navigationHelpButton: false,
                    homeButton: false,
                    sceneModePicker: true,
                    animation: false,
                    timeline: false,
                    fullscreenButton: true
                });

                // Enable terrain
                viewer.scene.globe.enableLighting = true;
                viewer.scene.globe.terrainExaggeration = 1.0;
                viewer.scene.globe.enableLighting = true;
                
                // Function to add a pin at specific coordinates
                function addPin(lat, lon, label, color) {
                    try {
                        const pinColor = color || Cesium.Color.RED;
                        viewer.entities.add({
                            position: Cesium.Cartesian3.fromDegrees(lon, lat),
                            billboard: {
                                image: 'https://upload.wikimedia.org/wikipedia/commons/8/88/Map_marker.svg',
                                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                                scale: 0.5
                            },
                            label: {
                                text: label,
                                font: '14px sans-serif',
                                fillColor: Cesium.Color.WHITE,
                                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                                outlineWidth: 2,
                                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                                pixelOffset: new Cesium.Cartesian2(0, -9)
                            }
                        });
                        return true;
                    } catch (error) {
                        console.error('Error adding pin:', error);
                        return false;
                    }
                }

                // Function to zoom to location
                function zoomToLocation(lat, lon, height = 1000000) {
                    try {
                        viewer.camera.flyTo({
                            destination: Cesium.Cartesian3.fromDegrees(lon, lat, height),
                            orientation: {
                                heading: Cesium.Math.toRadians(0),
                                pitch: Cesium.Math.toRadians(-45),
                                roll: 0.0
                            },
                            duration: 2
                        });
                        return true;
                    } catch (error) {
                        console.error('Error zooming:', error);
                        return false;
                    }
                }

                // Function to clear all entities
                function clearMap() {
                    try {
                        viewer.entities.removeAll();
                        return true;
                    } catch (error) {
                        console.error('Error clearing map:', error);
                        return false;
                    }
                }

                // Initial view - India
                zoomToLocation(20.5937, 78.9629, 5000000);
            </script>
        </body>
        </html>
        """

    def on_page_loaded(self, success):
        """Called when the web page finishes loading"""
        if (success):
            self.status_label.setText("Map loaded")
            # Set up a timer to periodically update coordinates
            self.coord_timer = QTimer(self)
            self.coord_timer.timeout.connect(self.update_coordinates)
            self.coord_timer.start(1000)  # Update every second
            
            # Enable forest plotting button
            self.plot_forests_button.setEnabled(True)
            
            # Auto-navigate to India to prepare for plotting forests
            QTimer.singleShot(1000, lambda: self.navigate_to_specific_country("India"))
        else:
            self.status_label.setText("Map load failed")
    
    def navigate_to_specific_country(self, country_name):
        """Programmatically navigate to a specific country"""
        self.input_field.setText(country_name)
        self.navigate_to_country()
    
    def update_coordinates(self):
        """Updates the current coordinates from the map view"""
        js_command = """
        (function() {
            if (typeof viewer !== 'undefined' && viewer && viewer.camera) {
                // Get the center of the screen (where the user is looking)
                const windowPosition = new Cesium.Cartesian2(
                    viewer.canvas.clientWidth / 2,
                    viewer.canvas.clientHeight / 2
                );
                
                
                const ray = viewer.camera.getPickRay(windowPosition);
                const cartesian = viewer.scene.globe.pick(ray, viewer.scene);
                
                // If we got a valid point, convert to lat/long
                if (cartesian) {
                    const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
                    const longitude = Cesium.Math.toDegrees(cartographic.longitude);
                    const latitude = Cesium.Math.toDegrees(cartographic.latitude);
                    const height = cartographic.height;
                    return {latitude: latitude, longitude: longitude, height: height};
                }
                
                // Fallback to camera position if no surface point found
                const position = viewer.camera.position;
                const camCartographic = Cesium.Cartographic.fromCartesian(position);
                const camLongitude = Cesium.Math.toDegrees(camCartographic.longitude);
                const camLatitude = Cesium.Math.toDegrees(camCartographic.latitude);
                const camHeight = camCartographic.height;
                return {latitude: camLatitude, longitude: camLongitude, height: camHeight};
            }
            return null;
        })();
        """
        self.browser.page().runJavaScript(js_command, self.handle_coordinates_result)
    
    def handle_coordinates_result(self, result):
        """Handles the coordinates result from JavaScript"""
        if result:
            self.current_latitude = result['latitude']
            self.current_longitude = result['longitude']
            self.coords_label.setText(f"Lat: {self.current_latitude:.6f}°, Lon: {self.current_longitude:.6f}°")
            
            # Enable capture button if we have valid coordinates
            if not self.capture_button.isEnabled() and not self.is_analyzing:
                self.capture_button.setEnabled(True)

    def navigate_to_country(self):
        """Moves the camera to the user-input country"""
        country_name = self.input_field.text().strip()
        if not country_name:
            return
            
        self.status_label.setText(f"Navigating to {country_name}...")
        self.is_loading = True
        self.capture_button.setEnabled(False)
        
        js_command = f"""
        goToCountry('{country_name}').then(success => {{ 
            return success ? '{country_name}' : 'FAILED'; 
        }});
        """
        self.browser.page().runJavaScript(js_command, self.handle_navigation_result)

    def handle_navigation_result(self, result):
        """Handles the navigation result from JavaScript"""
        self.is_loading = False
        
        if result == "FAILED":
            self.status_label.setText("Navigation failed")
            QMessageBox.warning(self, "Navigation Error", 
                               f"Could not find location. Please check the spelling and try again.")
        else:
            self.status_label.setText(f"Viewing {result}")
            self.capture_button.setEnabled(True)
            
            # If we've navigated to India, automatically plot forest locations
            if result=="india":
                QTimer.singleShot(1000, self.plot_indian_forests)

    def capture_screenshot(self):
        """Captures the screenshot and sends it to the DL model"""
        if self.is_analyzing:
            return
            
        self.is_analyzing = True
        self.status_label.setText("Capturing and analyzing...")
        self.progress_bar.setVisible(True)
        self.capture_button.setEnabled(False)
        
        # Create a timestamp for unique filename
        timestamp = int(time.time())
        screenshot_path = f"screenshot_{timestamp}.png"
        
        # Wait for any animations to complete, then capture
        QTimer.singleShot(500, lambda: self.save_screenshot(screenshot_path))

    def save_screenshot(self, screenshot_path):
        """Saves the screenshot properly"""
        self.browser.grab().save(screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")

        # Send to DL model for analysis
        self.send_to_model(screenshot_path)

    def send_to_model(self, img_path):
        """Sends screenshot to model API for analysis"""
        url = "http://127.0.0.1:8000/predict"
        if not os.path.exists(img_path):
            QMessageBox.critical(self, "File Error", f"Screenshot file not found: {img_path}")
            self.cleanup_after_error()
            return
            
        try:
            # Ensure file is properly opened and closed
            with open(img_path, 'rb') as img_file:
                files = {'file': ('image.jpg', img_file, 'image/jpeg')}
                data = {
                    'latitude': str(self.current_latitude),
                    'longitude': str(self.current_longitude)
                }
                
                response = requests.post(url, files=files, data=data, timeout=10)
                
                try:
                    result = response.json()
                except ValueError as e:
                    print(f"Invalid JSON response: {response.text}")
                    QMessageBox.critical(self, "Server Error", 
                                     f"Server returned invalid data. Response: {response.text[:200]}")
                    self.cleanup_after_error()
                    return
                    
                if response.status_code == 200:
                    if not isinstance(result, dict):
                        raise ValueError(f"Expected dictionary response, got {type(result)}")
                    self.display_results(result)
                else:
                    error_msg = result.get('detail', response.text) if isinstance(result, dict) else response.text
                    print(f"Server error {response.status_code}: {error_msg}")
                    QMessageBox.critical(self, "Server Error", 
                                     f"Server error {response.status_code}: {error_msg}")
                    self.cleanup_after_error()
                    
        except requests.exceptions.ConnectionError:
            print(f"Connection error: API server not running at {url}")
            QMessageBox.critical(self, "Connection Error", 
                             f"Could not connect to the model API at {url}. Make sure the server is running.")
            self.cleanup_after_error()
            
        except Exception as e:
            print(f"Error sending to model: {str(e)}")
            QMessageBox.critical(self, "Analysis Error", 
                             f"Error during analysis: {str(e)}")
            self.cleanup_after_error()
            
        finally:
            # Clean up the screenshot file
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception as e:
                print(f"Error cleaning up file {img_path}: {str(e)}")

    def cleanup_after_error(self):
        """Helper method to clean up UI state after an error"""
        self.progress_bar.setVisible(False)
        self.is_analyzing = False
        self.capture_button.setEnabled(True)
        self.status_label.setText("Analysis failed")

    def display_results(self, data):
        """Displays the analysis results with comparison visualization"""
        try:
            # Get existing DL model results
            deforestation_score = data.get('deforestation_score', 0)
            timestamp = data.get('timestamp', int(time.time()))
            date_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            
            # Get coordinates
            lat = data.get('latitude', self.current_latitude)
            lon = data.get('longitude', self.current_longitude)
            
            # Store basic data in blockchain
            if self.blockchain:
                blockchain_result = self.blockchain.store_deforestation_alert(
                    latitude=lat,
                    longitude=lon,
                    deforestation_score=deforestation_score
                )
                
                if blockchain_result["status"] == "success":
                    print(f"Alert stored in blockchain. Transaction hash: {blockchain_result['transaction_hash']}")
                else:
                    print(f"Blockchain storage: {blockchain_result['message']}")

            # Create visualization window
            self.comparison_window = QWidget()
            layout = QVBoxLayout()
            
            # Add result labels
            layout.addWidget(QLabel(f"Location: {lat:.6f}°, {lon:.6f}°"))
            layout.addWidget(QLabel(f"Analysis Date: {date_time}"))
            layout.addWidget(QLabel(f"Current Deforestation Score: {deforestation_score*100}%"))
            
            # Add blockchain transaction info if available
            if self.blockchain and blockchain_result.get("status") == "success":
                layout.addWidget(QLabel("Blockchain Transaction Info:"))
                layout.addWidget(QLabel(f"Status: {'DEFORESTED' if deforestation_score > 0.4 else 'FOREST'}"))
                layout.addWidget(QLabel(f"Transaction Hash: {blockchain_result['transaction_hash'][:20]}..."))
                layout.addWidget(QLabel(f"Block Number: {blockchain_result['block_number']}"))

            # Rest of the visualization code...
            # Get historical data from com.py
            historical_data = get_deforestation_data(lat, lon)
            deforestation_score = deforestation_score * 100

            # Store results in blockchain
            if self.blockchain:
                blockchain_result = self.blockchain.store_deforestation_alert(
                    latitude=lat,
                    longitude=lon,
                    deforestation_score=deforestation_score/100  # Convert back to 0-1 scale
                )
                
                if blockchain_result["status"] == "success":
                    print(f"Alert stored in blockchain. Transaction hash: {blockchain_result['transaction_hash']}")
                else:
                    print(f"Blockchain storage: {blockchain_result['message']}")

            # Create visualization window
            self.comparison_window = QWidget()
            layout = QVBoxLayout()
            
            # Add result labels
            layout.addWidget(QLabel(f"Location: {lat:.6f}°, {lon:.6f}°"))
            layout.addWidget(QLabel(f"Analysis Date: {date_time}"))
            layout.addWidget(QLabel(f"Current Deforestation Score: {deforestation_score}%"))
            
            # Add blockchain transaction info if available
            if self.blockchain and blockchain_result.get("status") == "success":
                layout.addWidget(QLabel("Blockchain Transaction Info:"))
                layout.addWidget(QLabel(f"Transaction Hash: {blockchain_result['transaction_hash'][:20]}..."))
                layout.addWidget(QLabel(f"Block Number: {blockchain_result['block_number']}"))

            # Create matplotlib figure
            fig = plt.figure(figsize=(10, 6))
            ax = fig.add_subplot(111)
            
            # Plot historical data
            years = [d['year'] for d in historical_data['historical_data']]
            historical_values = [d['deforestation_percent'] for d in historical_data['historical_data']]
            ax.plot(years, historical_values, 'b-o', label='Historical Data')
            
            # Plot current DL prediction
            current_year = datetime.now().year
            ax.plot(current_year, deforestation_score, 'r*', markersize=15, label='Current DL Prediction')
            
            ax.set_title('Deforestation Analysis Comparison')
            ax.set_xlabel('Year')
            ax.set_ylabel('Deforestation Percentage (%)')
            ax.grid(True)
            ax.legend()
            
            # Create canvas widget
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            
            # Add to window
            self.comparison_window.setLayout(layout)
            self.comparison_window.setWindowTitle("Deforestation Analysis Comparison")
            self.comparison_window.resize(800, 600)
            self.comparison_window.show()
            
            # Save results
            result_file = f"analysis_result_{timestamp}.txt"
            with open(result_file, 'w') as f:
                f.write(f"Deforestation Analysis Results\n")
                f.write(f"Date: {date_time}\n")
                f.write(f"Location: {lat:.6f}°, {lon:.6f}°\n")
                f.write(f"Classification: {classification}\n")
                f.write(f"Current Deforestation Score: {deforestation_score:.2f}%\n")
                f.write(f"Confidence: {confidence:.2%}\n")
                f.write("\nHistorical Data:\n")
                for d in historical_data['historical_data']:
                    f.write(f"Year {d['year']}: {d['deforestation_percent']}%\n")
        
        except Exception as e:
            print(f"Error in display_results: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to display results: {str(e)}")
    
    def plot_coordinates(self, lat, lon, score=None):
        """Plot the coordinates on the map with a pin"""
        # Create label text based on score if available
        label = f"Score: {score:.1f}" if score is not None else "Analysis Point"
        
        # Determine color based on deforestation score (red for high, green for low)
        color = None  # Default color
        if score is not None:
            # Convert score to a color value - we'll use JavaScript for this
            js_color = f"""
            (function() {{
                // Scale from green (low) to red (high) based on score
                const value = Math.min(Math.max({score}/100, 0), 1);
                return new Cesium.Color(value, 1.0 - value, 0.0, 1.0);
            }})()
            """
            color = js_color
        
        # Create the pin at the coordinates
        js_command = f"""
        addPin({lat}, {lon}, "{label}", {color if color else "Cesium.Color.RED"});
        """
        self.browser.page().runJavaScript(js_command)
        
        # Zoom to the location
        js_command = f"""
        zoomToLocation({lat}, {lon}, 25000);
        """
        self.browser.page().runJavaScript(js_command)
        
        print(f"Plotted coordinates: Lat {lat}, Lon {lon}, Score {score}")
    def open_poaching_window(self):
        """Open the poaching detection window from 1.py"""
        try:
            self.hide()  # Hide the current window
            self.poaching_window = ForestMonitoringApp()
            self.poaching_window.show()
            
            # Connect the close event to show the main window again
            self.poaching_window.closeEvent = lambda event: self.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open poaching detection: {str(e)}")
            self.show()

    def plot_indian_forests(self):
        try:
            self.browser.page().runJavaScript("clearMap();")
            self.status_label.setText("Processing forest data...")
            self.progress_bar.setVisible(True)
            self.plot_forests_button.setEnabled(False)

            # Process all coordinates into points
            forest_dict = {'points': []}
            
            # Extended coordinates array with 100+ forest locations
            coordinates_array = [
                [93.039985657, 12.126609802], [93.037185669, 12.133360863],
                [93.043205261, 12.155815125], [93.036476135, 12.156920433],
                [93.037528992, 12.159742355], [93.044113159, 12.159362793],
                [93.055801392, 12.190261841], [93.068603516, 12.211334229],
                [93.076339722, 12.209576607], [93.077209473, 12.202170372],
                [93.086616516, 12.193051338], [75.134307861, 12.189311028],
                [75.134025574, 12.18735981], [75.131813049, 12.191531181],
                [75.147361755, 12.135416031], [75.157371521, 12.110160828],
                [76.435211, 30.759006], [77.216721, 28.644800],  # Delhi Ridge Forest
                [77.265417, 28.524154], [76.938876, 28.459497],  # Asola Wildlife Sanctuary
                [77.212691, 28.674610], [77.233558, 28.553392],  # Lodhi Gardens
                [77.593475, 12.972442], [77.584791, 12.891198],  # Bannerghatta
                [74.867256, 12.914144], [75.072414, 15.347077],  # Western Ghats
                [76.658234, 10.421725], [76.653771, 10.536722],  # Silent Valley
                [76.435547, 9.478853], [76.394348, 9.553192],    # Periyar
                [92.737121, 11.671312], [92.730627, 11.623853],  # Andaman forests
                [77.147378, 8.679825], [77.537682, 8.553732],    # Agasthyamalai
                [80.283111, 13.082680], [80.284527, 13.073164],  # Guindy
                [91.734228, 26.138910], [91.736460, 26.140108],  # Kaziranga
                [79.420765, 11.937625], [79.419928, 11.936537],  # Tamil Nadu forests
                [73.464576, 18.349667], [73.467966, 18.348478],  # Maharashtra forests
                [84.868427, 22.213745], [84.869717, 22.214689],  # Jharkhand forests
                [94.562383, 26.610243], [94.563673, 26.611187],  # Nagaland forests
                [77.973601, 30.128812], [77.974891, 30.129756],  # Uttarakhand forests
                [88.363892, 22.538513], [88.365182, 22.539457],  # Sundarbans
                [76.083984, 14.167188], [76.085274, 14.168132],  # Karnataka forests
                [91.736460, 25.574396], [91.737750, 25.575340],  # Meghalaya forests
                [94.108683, 27.057437], [94.109973, 27.058381],  # Arunachal forests
                [85.324336, 23.350115], [85.325626, 23.351059],  # Ranchi forests
                [75.317383, 19.997377], [75.318673, 19.998321],  # Ajanta forests
                [93.916234, 24.663728], [93.917524, 24.664672],  # Manipur forests
                [92.936892, 26.183960], [92.938182, 26.184904],  # Assam forests
                [76.957031, 8.537565], [76.958321, 8.538509],    # Kerala forests
                [78.685973, 17.375278], [78.687263, 17.376222],  # Hyderabad urban forests
                [73.019072, 19.214434], [73.020362, 19.215378],  # Sanjay Gandhi National Park
                [77.265625, 28.613459], [77.266915, 28.614403],  # Delhi NCR green areas
                [88.147417, 27.340889], [88.148707, 27.341833],  # Sikkim forests
                [74.312868, 31.582418], [74.314158, 31.583362],  # Punjab forests
                [75.857376, 22.719568], [75.858666, 22.720512],  # Madhya Pradesh forests
                [85.279012, 25.594095], [85.280302, 25.595039],  # Bihar forests
                [81.866870, 25.435801], [81.868160, 25.436745],  # Uttar Pradesh forests
                [71.577956, 22.309426], [71.579246, 22.310370],  # Gujarat forests
                [73.855860, 15.492950], [73.857150, 15.493894],  # Goa forests
                [91.988002, 23.164091], [91.989292, 23.165035],  # Tripura forests
                [78.474228, 17.361376], [78.475518, 17.362320],  # Telangana forests
                [83.896447, 18.766336], [83.897737, 18.767280],  # Odisha forests
                [74.634586, 26.449896], [74.635876, 26.450840],  # Rajasthan forests
                [79.073193, 21.145800], [79.074483, 21.146744],  # Central India forests
                [93.936431, 24.813968], [93.937721, 24.814912],  # Northeast forests
                # Additional points spread across different regions
                [76.957031, 8.537565], [77.594384, 12.971891],   # Southern forests
                [73.019072, 19.214434], [72.877426, 19.076891],  # Western forests
                [88.363892, 22.538513], [87.747426, 22.987651],  # Eastern forests
                [77.265625, 28.613459], [77.198772, 28.543924],  # Northern forests
                [78.486671, 17.385044], [78.315239, 17.412725],  # Central forests
            ]

            # Convert all coordinates to points
            for i, coord in enumerate(coordinates_array):
                forest_dict['points'].append({
                    'lon': coord[0],
                    'lat': coord[1],
                    'name': f'Forest Area {i+1}'
                })

            # Rest of the plotting code remains the same
            js_points = []
            for point in forest_dict['points']:
                js_point = f"{{lat: {point['lat']}, lon: {point['lon']}, name: '{point['name']}'}}"
                js_points.append(js_point)

            if js_points:
                # First zoom out to show all of India
                self.browser.page().runJavaScript("""
                zoomToLocation(22.3511148, 78.6677428, 3000000);
                """)

                

                # Plot all points in batch
                points_array = "[" + ",".join(js_points) + "]"
                js_command = f"""
                (function() {{
                    const points = {points_array};
                    for (const point of points) {{
                        viewer.entities.add({{
                            position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat),
                            point: {{
                                pixelSize: 5,
                                color: Cesium.Color.GREEN.withAlpha(0.8),
                                outlineColor: Cesium.Color.WHITE,
                                outlineWidth: 1
                            }},
                            label: {{
                                text: point.name,
                                font: '10px sans-serif',
                                fillColor: Cesium.Color.WHITE,
                                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                                outlineWidth: 1,
                                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                                pixelOffset: new Cesium.Cartesian2(0, -6),
                                show: false
                            }}
                        }});
                    }}
                    return points.length;
                }})();
                """
                
                self.browser.page().runJavaScript(js_command, self.handle_forest_plotting_complete)

            # ...existing code...

        except Exception as e:
            self.progress_bar.setVisible(False)
            self.plot_forests_button.setEnabled(True)
            print(f"Error plotting forests: {str(e)}")
            QMessageBox.critical(self, "Plotting Error", f"Failed to plot forests: {str(e)}")
            self.status_label.setText("Plot failed")

    def handle_forest_plotting_complete(self, count):
        """Handle completion of forest plotting"""
        self.progress_bar.setVisible(False)
        self.plot_forests_button.setEnabled(True)
        self.status_label.setText(f"Plotted {count} forest locations")
        print(f"Successfully plotted {count} forest locations")

    def MarkedPlace(self, lat, lon):
        """Mark specific places on the map"""
        # This function is kept for compatibility but its functionality
        # is now merged into plot_indian_forests
        self.plot_indian_forests()
        
        # Also plot the specific lat/lon if provided
        if lat and lon:
            js_command = f"""
            addPin({lat}, {lon}, "Marked Location", Cesium.Color.BLUE);
            """
            self.browser.page().runJavaScript(js_command)
            

class PoachingDetectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.recording = False

    def init_ui(self):
        self.setWindowTitle("Forest Poaching Detection")
        self.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()

        # YouTube video player (forest surveillance feed)
        self.web_view = QWebEngineView()
        self.web_view.setHtml(f"""
            <html>
                <body>
                    <iframe width="100%" height="400"
                        src="https://youtu.be/JAxLC-Vvuz8?si=W-P9VmGbPbCR-Vf4"
                        frameborder="0" allowfullscreen>
                    </iframe>
                </body>
            </html>
        """)
        layout.addWidget(self.web_view)

        # Control buttons
        button_layout = QHBoxLayout()
        
        self.capture_image_btn = QPushButton("Capture Image")
        self.capture_image_btn.clicked.connect(self.capture_image)
        button_layout.addWidget(self.capture_image_btn)

        self.record_audio_btn = QPushButton("Start Recording Audio")
        self.record_audio_btn.clicked.connect(self.toggle_audio_recording)
        button_layout.addWidget(self.record_audio_btn)

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Results display
        self.results_label = QLabel("Detection Results:")
        layout.addWidget(self.results_label)

        self.setLayout(layout)

    def capture_image(self):
        self.status_label.setText("Capturing image...")
        timestamp = int(time.time())
        image_path = f"poaching_capture_{timestamp}.png"
        
        # Capture the current frame
        self.web_view.grab().save(image_path)
        
        # Send to model for analysis
        self.analyze_capture(image_path)

    def toggle_audio_recording(self):
        if not self.recording:
            self.recording = True
            self.record_audio_btn.setText("Stop Recording")
            self.status_label.setText("Recording audio...")
            # Start audio recording logic here
        else:
            self.recording = False
            self.record_audio_btn.setText("Start Recording Audio")
            self.status_label.setText("Audio recording stopped")
            # Stop audio recording and analyze

    def analyze_capture(self, image_path):
        try:
            url = "http://127.0.0.1:8000/detect_poaching"
            files = {'file': open(image_path, 'rb')}
            
            self.status_label.setText("Analyzing capture...")
            
            response = requests.post(url, files=files)
            if response.status_code == 200:
                result = response.json()
                self.display_results(result)
            else:
                self.status_label.setText("Analysis failed")
                QMessageBox.warning(self, "Error", "Failed to analyze capture")
        
        except Exception as e:
            self.status_label.setText("Error during analysis")
            QMessageBox.critical(self, "Error", f"Analysis error: {str(e)}")
        finally:
            files['file'].close()

    def display_results(self, results):
        detection_text = f"""
        Threat Level: {results.get('threat_level', 'Unknown')}
        Confidence: {results.get('confidence', 0):.2f}%
        Detected Objects: {', '.join(results.get('detected_objects', []))}
        """
        self.results_label.setText(detection_text)
        
        if results.get('threat_level', '').lower() == 'high':
            QMessageBox.warning(self, "Alert", "High threat level detected!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())