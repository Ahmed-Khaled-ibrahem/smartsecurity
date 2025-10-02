import cv2
import numpy as np
import mediapipe as mp
from aiortc import VideoStreamTrack, RTCPeerConnection, RTCSessionDescription
from av import VideoFrame
from picamera2 import Picamera2
import asyncio, json, aiohttp, aiohttp.web, time
import firebase_admin
from firebase_admin import credentials, db
import requests, sseclient
import threading
from collections.abc import MutableMapping
import pyrebase
import RPi.GPIO as GPIO
import time
import threading
from mpu6050 import mpu6050

# Pins
BUZZER_PIN = 27
RELAY_PIN = 17

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)   # suppress reuse warnings
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Setup MPU6050
# mpu = mpu6050(0x68)

# Accident detection function
def detect_accident():
    pass
    # accel = mpu.get_accel_data()
    # ax, ay, az = accel['x'], accel['y'], accel['z']
    # upside_down = az < -7
    # sudden_move = abs(ax) > 12 or abs(ay) > 12 or abs(az) > 15
    # if upside_down or sudden_move:
    #     print("🚨 Accident Detected!")
    #     buzzer_queick_beep()
    #     if alerts and contacts_flag:
    #         buzzer_queick_beep()
    #         send_alerts_to_contacts()


alerts = False;
buzzer = False;
contacts_flag = False;
vibration = False;
contactsList = [];
alertState = False;


def buzzer_queick_beep():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    GPIO.output(RELAY_PIN, GPIO.HIGH)

    time.sleep(0.1)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.output(RELAY_PIN, GPIO.LOW)

    time.sleep(0.1)
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    GPIO.output(RELAY_PIN, GPIO.HIGH)

    time.sleep(0.1)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.output(RELAY_PIN, GPIO.LOW)

def send_alerts_to_contacts():
    global contactsList
    for contact in contactsList:
        print(f"Sending alert to {contact}")
        # Integrate with SMS/Email API here


# ----- Your Detection Class -----
class DrowsinessDetector:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        self.EYE_AR_THRESH = 0.25
        self.EYE_AR_CONSEC_FRAMES = 20
        self.counter = 0
        self.status_text = "No Face Detected"

    def eye_aspect_ratio(self, eye_points, landmarks, w, h):
        pts = [(int(landmarks[p].x * w), int(landmarks[p].y * h)) for p in eye_points]
        A = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
        B = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
        C = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
        return (A + B) / (2.0 * C), pts

    def process(self, frame):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                leftEAR, leftPts = self.eye_aspect_ratio(self.LEFT_EYE, face_landmarks.landmark, w, h)
                rightEAR, rightPts = self.eye_aspect_ratio(self.RIGHT_EYE, face_landmarks.landmark, w, h)
                ear = (leftEAR + rightEAR) / 2.0

                # Draw eyes
                for (x, y) in leftPts + rightPts:
                    cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

                if ear < self.EYE_AR_THRESH:
                    self.counter += 1
                    if self.counter >= self.EYE_AR_CONSEC_FRAMES:
                        self.status_text = "DROWSINESS ALERT!"
                        print("Drowsiness Detected!")
                        asyncio.create_task(updateDatabaseDetection(True))
                else:
                    self.counter = 0
                    self.status_text = "Normal"
                    asyncio.create_task(updateDatabaseDetection(False))

        else:
            self.status_text = "No Face Detected"
            asyncio.create_task(updateDatabaseDetection(False))

        # Overlay text
        # cv2.putText(frame, f"Status: {self.status_text}", (10, 30),
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.8,
        #             (0, 0, 255) if "ALERT" in self.status_text else (0, 255, 0), 2)
        return frame


async def updateDatabaseDetection(detected):
    global helper, alerts, buzzer, vibration

    if detected and buzzer:
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
    else:
        GPIO.output(BUZZER_PIN, GPIO.LOW)

    if detected and vibration:
        GPIO.output(RELAY_PIN, GPIO.HIGH)
    else:
        GPIO.output(RELAY_PIN, GPIO.LOW)

    if alerts == True :
        global alertState
        if detected != alertState:
            print("Updating detection status in Firebase:", detected)
            helper.update("live", {"detected": detected})
            alertState = detected


# ----- WebRTC Video Track -----
class CameraStreamTrack(VideoStreamTrack):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.detector = DrowsinessDetector()


    async def recv(self):
        frame = self.picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        # Run AI detection
        frame = self.detector.process(frame)
        # Convert to WebRTC VideoFrame
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts, video_frame.time_base = await self.next_timestamp()
        return video_frame

class FirebaseHelper:
    def __init__(self, cred_path, db_url, pyrebase_config):
        # Firebase Admin SDK for writes/reads
        cred = credentials.Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': db_url
            })
        self.ref = db.reference("/")
        
        # Pyrebase for streaming/listening
        self.firebase = pyrebase.initialize_app(pyrebase_config)
        self.pb_db = self.firebase.database()

    def write(self, path, value):
        """Write data to a specific path"""
        self.ref.child(path).set(value)

    def update(self, path, value_dict):
        """Update values at a path"""
        if not isinstance(value_dict, dict) or not value_dict:
            raise ValueError("Value argument must be a non-empty dictionary.")
        self.ref.child(path).update(value_dict)

    def read(self, path):
        """Read data from a path"""
        return self.ref.child(path).get()

    def listen(self, callback):
        def stream_handler(message):
            callback(message)
        # self.pb_db.child(path).stream(stream_handler)
        self.pb_db.stream(stream_handler)

picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (640, 480)})
picam2.configure(config)

# ----- WebRTC Signaling -----
async def offer(request):
    params = await request.json()
    pc = RTCPeerConnection()
    # Create a single Picamera2 instance
    picam2.start()
    pc.addTrack(CameraStreamTrack(picam2))

    await pc.setRemoteDescription(RTCSessionDescription(sdp=params["sdp"], type=params["type"]))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return aiohttp.web.Response(
        content_type="application/json",
        text=json.dumps({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}),
    )

def on_change(message):
    global contacts_flag, alerts, buzzer, vibration

    print("Path:", message["path"])
    print("Data:", message["data"])
    if message["path"] == "/": 
        data = message["data"]["settings"]
        alerts = data.get("alerts")
        buzzer = data.get("buzzer")
        contacts_flag = data.get("contacts")
        vibration = data.get("vibration")

    if message["path"] == "/settings":
        
        if message["data"].get("contacts") != None:
            contacts_flag = message["data"].get("contacts")
        if message["data"].get("alerts")!= None :
            alerts = message["data"].get("alerts")
        if message["data"].get("buzzer")!= None:
            buzzer = message["data"].get("buzzer")
        if message["data"].get("vibration")!= None:
            vibration = message["data"].get("vibration")

        # print(f"Contacts setting updated: {contacts_flag}")
        # print(f"Alerts setting updated: {alerts}")
        # print(f"Buzzer setting updated: {buzzer}")
        # print(f"Vibration setting updated: {vibration}")
        
    if message["path"] == "/raspi/status/online":
        status = message["data"]
        if not status:
            helper.update("raspi/status", {"online": True})

def get_ngrok_url():
    try:
        # ngrok's local API endpoint
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = response.json()
        
        # Loop through tunnels and find the http tunnel
        for tunnel in data.get("tunnels", []):
            if tunnel.get("proto") == "https":
                return tunnel.get("public_url")
        
        # fallback: return first tunnel if no https found
        if data.get("tunnels"):
            return data["tunnels"][0].get("public_url")
        
        return None
    except Exception as e:
        print("Error getting ngrok URL:", e)
        return None

def sensor_loop():
    while True:
        detect_accident()
        time.sleep(0.2)

pyrebase_config = {
    "apiKey": "AIzaSyClsZ-ZxaQUUKvn0KHHnOw4lNEjxYIyYv8",
    "authDomain": "smartparking-12902.firebaseapp.com",
    "databaseURL": "https://smartparking-12902-default-rtdb.firebaseio.com",
    "storageBucket": "smartparking-12902.firebasestorage.app",
}

helper = FirebaseHelper(
    cred_path="serviceAccountKey.json",
    db_url="https://smartparking-12902-default-rtdb.firebaseio.com",
    pyrebase_config=pyrebase_config
)

# ----- Run Web Server -----
app = aiohttp.web.Application()
app.router.add_post("/offer", offer)

if __name__ == "__main__":
    # Write value
    helper.write("raspi/status", {"online": True})
    # Read value
    print("Current status:", helper.read("live/active"))
    # Update part of path
    helper.update("live", {"active": True})

    # Start thread
    thread = threading.Thread(target=sensor_loop, daemon=True)
    thread.start()

    # Create the listener thread
    listener_thread = threading.Thread(
        target=helper.listen,
        args=(on_change,),
        daemon=True  # Daemon so it exits when main program exits
    )

    # Start listening in background
    listener_thread.start()
    # Listen for changes
    url = get_ngrok_url()
    if url:
        print("Ngrok public URL:", url)
        helper.update("live", {"url": url})
        aiohttp.web.run_app(app, port=8080)
    else:
        print("No ngrok URL found")
        GPIO.cleanup()
    
