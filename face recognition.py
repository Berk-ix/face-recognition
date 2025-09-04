# -*- coding: utf-8 -*-
import sys, os, cv2, sqlite3, pickle, urllib.request, numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QMessageBox, QFrame, QListWidget, QListWidgetItem)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt

MODEL_PROTO = "deploy.prototxt"
MODEL_WEIGHTS = "res10_300x300_ssd_iter_140000.caffemodel"
MODEL_URLS = {
    MODEL_PROTO: "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt",
    MODEL_WEIGHTS: "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
}
DB_NAME = "faces.db"
DATASET_DIR = "dataset"
CROWN_PATH = "crown.png"
FACE_SIZE = (100, 100)
CONFIDENCE_THRESHOLD = 0.6
SIMILARITY_THRESHOLD = 0.8

def ensure_models():
    for file, url in MODEL_URLS.items():
        if not os.path.exists(file):
            urllib.request.urlretrieve(url, file)

def create_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS faces (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, embedding BLOB)")
        conn.commit()

def save_face_to_db(name, embedding):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT INTO faces (name, embedding) VALUES (?, ?)", (name, pickle.dumps(embedding)))
        conn.commit()

def delete_all_faces():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM faces")
        conn.commit()

def load_faces_from_db():
    with sqlite3.connect(DB_NAME) as conn:
        rows = conn.execute("SELECT name, embedding FROM faces").fetchall()
    return [r[0] for r in rows], [pickle.loads(r[1]) for r in rows]

def get_face_embedding(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, FACE_SIZE)
    return resized.flatten().astype("float32")/255.0

def overlay_crown(frame, x, y, w, h):
    crown = cv2.imread(CROWN_PATH, cv2.IMREAD_UNCHANGED)
    if crown is None: return frame, y
    cw, ch = w, int(h*0.3)
    crown = cv2.resize(crown, (cw, ch))
    cx, cy = x, max(y-ch, 0)
    if crown.shape[2] == 4:
        a = crown[:,:,3]/255.0; b = 1.0-a
        for c in range(3):
            frame[cy:cy+ch, cx:cx+cw, c] = a*crown[:,:,c] + b*frame[cy:cy+ch, cx:cx+cw, c]
    else:
        frame[cy:cy+ch, cx:cx+cw] = crown[:,:,:3]
    return frame, cy

class FaceRecognitionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.resize(1200, 750)
        os.makedirs(DATASET_DIR, exist_ok=True)
        ensure_models()
        self.face_net = cv2.dnn.readNetFromCaffe(MODEL_PROTO, MODEL_WEIGHTS)
        create_db()
        self.names, self.embeddings = load_faces_from_db()
        self.cam = None
        self.unknown_face_img = None
        self.timer = QTimer(); self.timer.timeout.connect(self.update_frame)

        root = QHBoxLayout(self)
        root.setContentsMargins(20,20,20,20); root.setSpacing(20)

        # Camera view
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(850, 600)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setObjectName("CameraLabel")

        left_card = QFrame()
        left_layout = QVBoxLayout(left_card)
        left_layout.addWidget(self.camera_label)
        root.addWidget(left_card, 7)

        # Right panel
        right_card = QFrame(); right_card.setObjectName("RightCard")
        right_layout = QVBoxLayout(right_card); right_layout.setSpacing(15)

        title = QLabel("Controls"); title.setObjectName("Title")
        self.preview = QLabel("Awaiting Face…")
        self.preview.setFixedSize(280,280)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setObjectName("Preview")

        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("Enter Name")

        self.btn_save = QPushButton("💾 Save Face"); self.btn_save.clicked.connect(self.save_new_face)
        self.btn_clear = QPushButton("🗑️ Clear All"); self.btn_clear.clicked.connect(self.clear_all_faces)
        self.btn_refresh = QPushButton("🔄 Refresh"); self.btn_refresh.clicked.connect(self.refresh_list)
        self.btn_format = QPushButton("💥 Format DB"); self.btn_format.clicked.connect(self.format_all)
        self.btn_del = QPushButton("❌ Delete Selected"); self.btn_del.clicked.connect(self._delete_selected)

        self.list_faces = QListWidget(); self.list_faces.setObjectName("FacesList")

        right_layout.addWidget(title)
        right_layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.name_input)
        right_layout.addWidget(self.btn_save)
        right_layout.addWidget(self.btn_clear)
        right_layout.addWidget(self.btn_refresh)
        right_layout.addWidget(self.btn_format)
        right_layout.addWidget(self.list_faces, 1)
        right_layout.addWidget(self.btn_del)

        root.addWidget(right_card, 3)

        self._apply_style()
        self._populate_list()
        self.start_camera()

    def _apply_style(self):
        self.setStyleSheet("""
            QWidget { background: #0f1115; color: #e6e6e6; font-family: 'Segoe UI','Inter',Arial; font-size: 14px; }
            #Title { font-size: 20px; font-weight: bold; margin-bottom: 10px; }
            #CameraLabel { background: qradialgradient(cx:0.5, cy:0.5, radius:1.0, fx:0.5, fy:0.5,
                              stop:0 #0b0d11, stop:1 #151922);
                           border-radius: 18px; border: 3px solid rgba(0,240,255,0.3); }
            #RightCard { background: rgba(255,255,255,0.04); border-radius: 18px; padding: 15px; }
            #Preview { background: #111623; border: 2px dashed rgba(255,255,255,0.15); border-radius: 14px; }
            QPushButton { background-color: #1a1f2b; border: none; border-radius: 12px;
                          padding: 12px; font-size: 15px; font-weight: 600; color: #e6e6e6; }
            QPushButton:hover { background-color: #2a3242; }
            QPushButton:pressed { background-color: #101420; }
            QLineEdit { background: #141924; border: 1px solid rgba(255,255,255,0.07);
                        border-radius: 12px; padding: 10px; }
            #FacesList { background: #141924; border-radius: 12px; padding: 8px; }
        """)

    def _populate_list(self):
        self.list_faces.clear()
        for n in self.names:
            self.list_faces.addItem(QListWidgetItem(n))

    def _delete_selected(self):
        it = self.list_faces.currentItem()
        if not it: return
        name = it.text()
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM faces WHERE name = ?", (name,))
            conn.commit()
        self.names, self.embeddings = load_faces_from_db()
        self._populate_list()
        npy = os.path.join(DATASET_DIR, f"{name}.npy")
        if os.path.exists(npy): os.remove(npy)
        QMessageBox.information(self, "Done", f"'{name}' deleted.")

    def clear_all_faces(self):
        delete_all_faces()
        self.names, self.embeddings = [], []
        self._populate_list()
        QMessageBox.information(self, "Done", "All faces cleared.")

    def refresh_list(self):
        self.names, self.embeddings = load_faces_from_db()
        self._populate_list()
        QMessageBox.information(self, "Done", "List refreshed.")

    def format_all(self):
        # release db first
        delete_all_faces()
        try:
            if os.path.exists(DB_NAME):
                os.remove(DB_NAME)
        except PermissionError:
            # if locked, just truncate it
            with open(DB_NAME, "w"):
                pass

        if os.path.exists(DATASET_DIR):
            for f in os.listdir(DATASET_DIR):
                if f.endswith(".npy"):
                    try:
                        os.remove(os.path.join(DATASET_DIR, f))
                    except:
                        pass

        create_db()
        self.names, self.embeddings = [], []
        self._populate_list()
        QMessageBox.information(self, "Done", "Database and dataset formatted.")

    def start_camera(self):
        for idx in range(5):
            cap = cv2.VideoCapture(idx)
            ok, _ = cap.read()
            if ok:
                self.cam = cap; break
            cap.release()
        if not self.cam:
            QMessageBox.critical(self, "Error", "No camera found.")
            return
        self.timer.start(25)

    def detect_faces(self, frame):
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.face_net.setInput(blob)
        det = self.face_net.forward()
        faces = []
        for i in range(det.shape[2]):
            conf = det[0,0,i,2]
            if conf > CONFIDENCE_THRESHOLD:
                x1,y1,x2,y2 = (det[0,0,i,3:7]*np.array([w,h,w,h])).astype(int)
                x1,y1 = max(0,x1), max(0,y1)
                x2,y2 = min(w-1,x2), min(h-1,y2)
                faces.append((x1,y1,x2-x1,y2-y1))
        return faces

    def update_frame(self):
        if not self.cam: return
        ok, frame = self.cam.read()
        if not ok: return
        faces = self.detect_faces(frame)
        show_prev = False
        for (x,y,w,h) in faces:
            if w<=0 or h<=0: continue
            face = frame[y:y+h, x:x+w]
            if face.size==0: continue
            emb = get_face_embedding(face)
            name = "Unknown"
            text_y = max(0, y-12)
            if self.embeddings:
                sims = cosine_similarity([emb], self.embeddings)[0]
                best = int(np.argmax(sims))
                if sims[best] > SIMILARITY_THRESHOLD:
                    name = self.names[best]
                else:
                    self.unknown_face_img = face
                    show_prev = True
            else:
                self.unknown_face_img = face
                show_prev = True
            if name.lower()=="owner":
                frame, cy = overlay_crown(frame, x, y, w, h)
                text_y = max(0, cy-10)
            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,240,255), 2)
            if name!="Unknown":
                cv2.putText(frame, name, (x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,200), 2)
        if show_prev and self.unknown_face_img is not None:
            frgb = cv2.cvtColor(self.unknown_face_img, cv2.COLOR_BGR2RGB)
            h,w,ch = frgb.shape
            q = QImage(frgb.data, w, h, ch*w, QImage.Format.Format_RGB888)
            self.preview.setPixmap(QPixmap.fromImage(q).scaled(280,280, Qt.AspectRatioMode.KeepAspectRatio,
                                                               Qt.TransformationMode.SmoothTransformation))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h,w,ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch*w, QImage.Format.Format_RGB888)
        self.camera_label.setPixmap(QPixmap.fromImage(qimg).scaled(self.camera_label.width(), self.camera_label.height(),
                                                                   Qt.AspectRatioMode.KeepAspectRatio,
                                                                   Qt.TransformationMode.SmoothTransformation))

    def save_new_face(self):
        if self.unknown_face_img is None or self.unknown_face_img.size == 0:
            QMessageBox.warning(self, "Warning", "No unknown face to save.")
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Enter a name.")
            return
        emb = get_face_embedding(self.unknown_face_img)
        save_face_to_db(name, emb)
        np.save(os.path.join(DATASET_DIR, f"{name}.npy"), emb)
        self.names.append(name); self.embeddings.append(emb)
        self._populate_list()
        self.name_input.clear()
        self.unknown_face_img = None
        self.preview.setText("Awaiting Face…"); self.preview.setPixmap(QPixmap())
        QMessageBox.information(self, "Done", f"{name} saved.")

    def closeEvent(self, e):
        self.timer.stop()
        if self.cam: self.cam.release()
        cv2.destroyAllWindows()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = FaceRecognitionApp()
    w.show()
    sys.exit(app.exec())
