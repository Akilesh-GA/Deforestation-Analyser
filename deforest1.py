import sys
import os
import time
import cv2
import numpy as np
import pickle
import threading
import subprocess
import tempfile
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QPushButton, QLabel, QProgressBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap
import librosa
import soundfile as sf
import joblib

class VideoProcessingThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    analysis_ready = pyqtSignal(dict)
    audio_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, video_path, poaching_model_path, screenshot_interval=5):
        super().__init__()
        self.video_path = video_path
        self.poaching_model_path = poaching_model_path
        self.screenshot_interval = screenshot_interval
        self.running = True
        self.paused = False
        
    def run(self):
        try:
            # Load the poaching detection model
            self.load_poaching_model()
            
            # Open the video
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.error_occurred.emit(f"Error: Could not open video file {self.video_path}")
                return
                
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Extract audio to temporary file
            temp_audio_file = self.extract_audio()
            if temp_audio_file:
                self.audio_ready.emit(temp_audio_file)
            
            # Process video frames
            last_screenshot_time = time.time() - self.screenshot_interval  # To ensure first frame is captured
            
            while self.running:
                if self.paused:
                    time.sleep(0.1)
                    continue
                    
                ret, frame = cap.read()
                if not ret:
                    # Reached end of video, restart
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Emit the frame for display
                self.frame_ready.emit(frame)
                
                # Check if it's time to take a screenshot
                current_time = time.time()
                if current_time - last_screenshot_time >= self.screenshot_interval:
                    self.process_frame(frame)
                    last_screenshot_time = current_time
                
                # Control playback speed based on video FPS
                time.sleep(1/fps)
            
            cap.release()
            
        except Exception as e:
            self.error_occurred.emit(f"Error in video processing: {str(e)}")
    
    def load_poaching_model(self):
        try:
            self.poaching_model = joblib.load(self.poaching_model_path)
            print(f"Loaded poaching detection model from {self.poaching_model_path}")
        except Exception as e:
            self.error_occurred.emit(f"Failed to load poaching model: {str(e)}")
            self.poaching_model = None
    
    def extract_audio(self):
        try:
            # Create a temporary file for the audio
            temp_audio_file = tempfile.mktemp(suffix='.wav')
            
            # Check if ffmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except FileNotFoundError:
                self.error_occurred.emit("FFmpeg not found. Please install FFmpeg and add it to your system PATH")
                return None
            
            # Check if video file exists
            if not os.path.exists(self.video_path):
                self.error_occurred.emit(f"Video file not found: {self.video_path}")
                return None
                
            # Use ffmpeg to extract audio
            command = [
                'ffmpeg', 
                '-i', self.video_path, 
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM format
                '-ar', '44100',  # 44.1kHz
                '-ac', '2',  # Stereo
                '-y',  # Overwrite output file
                temp_audio_file
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                self.error_occurred.emit(f"FFmpeg error: {result.stderr}")
                return None
                
            print(f"Extracted audio to {temp_audio_file}")
            return temp_audio_file
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to extract audio: {str(e)}")
            return None
    
    def process_frame(self, frame):
        try:
            # Check if model is loaded
            if self.poaching_model is None:
                self.error_occurred.emit("Poaching model not loaded. Skipping analysis.")
                return
            
            # Prepare the image for the model
            img_features = self.extract_image_features(frame)
            if img_features is None:
                return
            
            # Make prediction using the poaching model
            predictions = self.poaching_model.predict(img_features, verbose=0)
            
            # For binary classification, get the probability of class 1
            confidence = float(predictions[0][0] * 100)
            
            # Determine threat level based on confidence threshold
            threat_level = "High" if confidence > 50 else "Low"
            
            # Create a list of detected objects (placeholder)
            detected_objects = ["Human", "Vehicle"] if threat_level == "High" else []
            
            # Save the frame as a temporary image file
            temp_img_path = tempfile.mktemp(suffix='.jpg')
            cv2.imwrite(temp_img_path, frame)
            
            # Prepare results
            results = {
                "threat_level": threat_level,
                "confidence": confidence,
                "detected_objects": detected_objects,
                "image_path": temp_img_path,
                "timestamp": time.time()
            }
            
            # Emit results
            self.analysis_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(f"Error processing frame: {str(e)}")
    
    def extract_image_features(self, frame):
        """Extract features from the image for the poaching detection model"""
        try:
            # Resize image to expected input size (224x224)
            resized = cv2.resize(frame, (224, 224))
            
            # Convert BGR to RGB (OpenCV uses BGR by default)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Normalize pixel values to [0, 1]
            normalized = rgb.astype(np.float32) / 255.0
            
            # Ensure shape is (1, 224, 224, 3) for model input
            processed = np.expand_dims(normalized, axis=0)
            
            return processed
            
        except Exception as e:
            print(f"Error in image preprocessing: {str(e)}")
            return None
    
    def stop(self):
        self.running = False
    
    def pause(self):
        self.paused = not self.paused
        return self.paused


class AudioAnalysisThread(QThread):
    analysis_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, audio_file, deact_script_path, bird_script_path):
        super().__init__()
        self.audio_file = audio_file
        self.deact_script_path = deact_script_path
        self.bird_script_path = bird_script_path
    
    def run(self):
        try:
            # Process audio with deact.py
            deact_results = self.process_with_deact()
            
            # Process audio with bird detection
            bird_results = self.process_with_bird_detection()
            
            # Combine results
            results = {
                "deact_results": deact_results,
                "bird_results": bird_results
            }
            
            self.analysis_complete.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(f"Error in audio analysis: {str(e)}")
    
    def process_with_deact(self):
        try:
            # Execute deact.py with the audio file
            command = [
                'python', 
                self.deact_script_path, 
                self.audio_file
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                print(f"Warning: deact.py returned non-zero exit code: {result.returncode}")
                print(f"Error output: {result.stderr}")
            
            # Parse the output (adjust based on your deact.py output format)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except Exception as e:
            print(f"Error executing deact.py: {str(e)}")
            return {"error": str(e)}
    
    def process_with_bird_detection(self):
        try:
            # Execute bird detection script with the audio file
            command = [
                'python', 
                self.bird_script_path, 
                self.audio_file
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                print(f"Warning: bird detection script returned non-zero exit code: {result.returncode}")
                print(f"Error output: {result.stderr}")
            
            # Parse the output (adjust based on your bird detection script output format)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except Exception as e:
            print(f"Error executing bird detection script: {str(e)}")
            return {"error": str(e)}


class ForestMonitoringApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Forest Monitoring System")
        self.setGeometry(100, 100, 1000, 800)
        
        self.video_folder = os.path.expanduser(r"C:\Users\dhars\Videos")  # Changed to videos directory
        self.current_video_path = os.path.expanduser(r"C:\Users\dhars\Videos\WhatsApp Video 2025-03-11 at 9.33.45 AM (1).mp4")  # Store specific video path
        self.poaching_model_path = r"F:\Deforest\Poaching Models\crypto_poaching.pkl"
        self.deact_script_path = r"F:\Deforest\Poaching Models\deact.py"
        self.bird_script_path = r"F:\Deforest\Poaching Models\Birdrs.pkl"
        
        # Initialize variables
        self.video_thread = None
        self.audio_thread = None
        self.current_video_path = None
        
        # Setup UI
        self.init_ui()
        
        # Check if folders and files exist
        self.check_requirements()
        self.back_button = QPushButton("Back to Main")
        self.back_button.clicked.connect(self.close)
    
    def init_ui(self):
        # Main widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Video display area
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black;")
        main_layout.addWidget(self.video_label)
        
        # Controls area
        controls_layout = QHBoxLayout()
        
        # Video controls
        self.play_button = QPushButton("Start Monitoring")
        self.play_button.clicked.connect(self.toggle_monitoring)
        controls_layout.addWidget(self.play_button)
        
        self.select_folder_button = QPushButton("Select Video Folder")
        self.select_folder_button.clicked.connect(self.select_video_folder)
        controls_layout.addWidget(self.select_folder_button)
        
        # Add controls layout to main layout
        main_layout.addLayout(controls_layout)
        
        # Status and progress area
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(status_layout)
        
        # Results area
        results_layout = QVBoxLayout()
        
        self.poaching_results_label = QLabel("Poaching Detection Results:")
        results_layout.addWidget(self.poaching_results_label)
        
        # self.audio_results_label = QLabel("Audio Analysis Results:")
        # results_layout.addWidget(self.audio_results_label)
        
        main_layout.addLayout(results_layout)
        
        # Set the main layout
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def check_requirements(self):
        # Check if video folder exists
        if not os.path.exists(self.video_folder):
            try:
                os.makedirs(self.video_folder)
                self.status_label.setText(f"Created video folder: {self.video_folder}")
            except Exception as e:
                self.status_label.setText(f"Error creating video folder: {str(e)}")
        
        # Check if poaching model exists
        if not os.path.exists(self.poaching_model_path):
            self.status_label.setText(f"Warning: Poaching model not found at {self.poaching_model_path}")
        
        # Check if scripts exist
        if not os.path.exists(self.deact_script_path):
            self.status_label.setText(f"Warning: deact.py not found at {self.deact_script_path}")
        
        if not os.path.exists(self.bird_script_path):
            self.status_label.setText(f"Warning: Bird script not found at {self.bird_script_path}")
    
    def select_video_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Folder", self.video_folder)
        if folder:
            self.video_folder = folder
            self.status_label.setText(f"Selected video folder: {folder}")
    
    def find_video_files(self):
        """Find all video files in the specified folder"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        videos = []
        
        if os.path.exists(self.video_folder):
            for file in os.listdir(self.video_folder):
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    videos.append(os.path.join(self.video_folder, file))
        
        return videos
    
    def toggle_monitoring(self):
        if self.video_thread is None or not self.video_thread.isRunning():
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        # Find available videos
        videos = self.find_video_files()
        
        if not videos:
            QMessageBox.warning(self, "No Videos Found", 
                f"No video files found in {self.video_folder}. Please add videos or select a different folder.")
            return
        
        # Use the first video for now
        self.current_video_path = videos[0]
        
        # Update UI
        self.play_button.setText("Stop Monitoring")
        self.status_label.setText(f"Monitoring from: {self.current_video_path}")
        self.progress_bar.setVisible(True)
        
        # Start video processing thread
        self.video_thread = VideoProcessingThread(
            self.current_video_path, 
            self.poaching_model_path
        )
        self.video_thread.frame_ready.connect(self.update_frame)
        self.video_thread.analysis_ready.connect(self.update_analysis_results)
        self.video_thread.audio_ready.connect(self.process_audio)
        self.video_thread.error_occurred.connect(self.handle_error)
        self.video_thread.start()
    
    def stop_monitoring(self):
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()
        
        # Update UI
        self.play_button.setText("Start Monitoring")
        self.status_label.setText("Monitoring stopped")
        self.progress_bar.setVisible(False)
    
    def update_frame(self, frame):
        """Update the video display with the current frame"""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        # Convert BGR (OpenCV) to RGB for Qt
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to QImage and then to QPixmap
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Scale pixmap to fit the label while maintaining aspect ratio
        pixmap = pixmap.scaled(self.video_label.width(), self.video_label.height(),
                                Qt.AspectRatioMode.KeepAspectRatio)
        
        # Set the pixmap to the label
        self.video_label.setPixmap(pixmap)
    
    def update_analysis_results(self, results):
        """Update UI with poaching detection results"""
        # Format the results
        detection_text = f"""
        Poaching Detection Results:
        - Confidence: {results.get('confidence', 0):.2f}%
        - Detected Objects: {', '.join(results.get('detected_objects', ['None']))}
        - Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results.get('timestamp', time.time())))}
        """
        
        self.poaching_results_label.setText(detection_text)
        
        # Show alert for high threat
        if results.get('threat_level', '').lower() == 'high':
            QMessageBox.warning(self, "Alert", "High poaching threat level detected!")
    
    def process_audio(self, audio_file):
        """Process the extracted audio file with deact.py and bird detection"""
        self.status_label.setText(f"Processing audio file: {audio_file}")
        
        # Start audio analysis thread
        self.audio_thread = AudioAnalysisThread(
            audio_file, 
            self.deact_script_path,
            self.bird_script_path
        )
        self.audio_thread.analysis_complete.connect(self.update_audio_results)
        self.audio_thread.error_occurred.connect(self.handle_error)
        self.audio_thread.start()
    
    def update_audio_results(self, results):
        """Update UI with audio analysis results"""
        # Format deact.py results
        deact_results = results.get('deact_results', {})
        deact_text = "Audio Analysis (deact.py):\n"
        
        if 'error' in deact_results:
            deact_text += f"- Error: {deact_results['error']}\n"
        else:
            deact_stdout = deact_results.get('stdout', '')
            deact_text += f"- Output: {deact_stdout[:200]}...\n" if len(deact_stdout) > 200 else f"- Output: {deact_stdout}\n"
        
        # Format bird detection results
        bird_results = results.get('bird_results', {})
        bird_text = "Bird Sound Detection:\n"
        
        if 'error' in bird_results:
            bird_text += f"- Error: {bird_results['error']}\n"
        else:
            bird_stdout = bird_results.get('stdout', '')
            bird_text += f"- Output: {bird_stdout[:200]}...\n" if len(bird_stdout) > 200 else f"- Output: {bird_stdout}\n"
        
        # Update the label
        self.audio_results_label.setText(deact_text + "\n" + bird_text)
    
    def handle_error(self, error_message):
        """Handle errors from threads"""
        self.status_label.setText(f"Error: {error_message}")
        print(f"Error: {error_message}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ForestMonitoringApp()
    window.show()
    sys.exit(app.exec())