import cv2
import time
import os
import sqlite3
import hashlib
import secrets
import numpy as np
import csv
from io import StringIO
import uvicorn
from fastapi import FastAPI, Request, Form, Response, Cookie, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from face_engine import FaceRecognizer

app = FastAPI()

os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("static/evidence", exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

recognizer = FaceRecognizer(det_size=(640, 640))

is_camera_on = True
ACTIVE_SESSIONS = {}  
system_stats = {
    "fps": 0.0, "inference_time": 0.0, 
    "matching_time": 0.0, "face_count": 0, "best_similarity": 0.0
}

# --- BỘ ĐỆM KHUÔN MẶT ĐỂ BẤM NÚT CHẤM CÔNG ---
# Lưu khuôn mặt xuất hiện trong 3 giây gần nhất: { "Name": (timestamp, face_crop_img) }
FACE_BUFFER = {}

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            image_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def hash_password(password: str, salt: bytes = None):
    if not salt:
        salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return pwd_hash.hex(), salt.hex()

def verify_password(password: str, password_hash: str, salt_hex: str):
    salt = bytes.fromhex(salt_hex)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return pwd_hash.hex() == password_hash

def get_current_user(session_token: str = Cookie(None)):
    if not session_token or session_token not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=303, detail="Chưa đăng nhập")
    return ACTIVE_SESSIONS[session_token]

def generate_frames():
    global system_stats, is_camera_on, FACE_BUFFER
    video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    frame_count = 0
    fps_start_time = time.time()
    fps_frame_counter = 0
    last_results = []    

    while True:
        if not is_camera_on:
            if video_capture.isOpened():
                video_capture.release()
            system_stats["fps"], system_stats["inference_time"], system_stats["face_count"] = 0.0, 0.0, 0
            
            blank_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(blank_frame, "CAMERA IS OFF", (450, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            ret, buffer = cv2.imencode('.jpg', blank_frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.5)
            continue

        if not video_capture.isOpened():
            video_capture.open(0, cv2.CAP_DSHOW)
            video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        success, frame = video_capture.read()
        if not success:
            time.sleep(0.1)
            continue

        frame_count += 1
        fps_frame_counter += 1

        elapsed_time = time.time() - fps_start_time
        if elapsed_time > 1.0:
            system_stats["fps"] = round(fps_frame_counter / elapsed_time, 1)
            fps_frame_counter = 0
            fps_start_time = time.time()

        if frame_count % 3 == 1:
            try:
                start_ai = time.time()
                results = recognizer.recognize(frame) 
                last_results = results  
                system_stats["inference_time"] = round((time.time() - start_ai) * 1000, 1)
                system_stats["face_count"] = len(results) if results else 0
            except Exception as e:
                results = last_results
        else:
            results = last_results

        current_time = time.time()

        if results:
            for res in results:
                try:
                    left, top, right, bottom = res["bbox"]
                    name = res.get("name", "Unknown")
                    sim = res.get("similarity", 0.0)

                    left, top, right, bottom = int(left), int(top), int(right), int(bottom)
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
                    cv2.rectangle(frame, (left, top - 40), (right, top), color, cv2.FILLED)
                    cv2.putText(frame, f"{name} ({round(sim*100, 1)}%)", (left + 8, top - 12), 
                                cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2)

                    # Lưu vào bộ đệm nếu nhận ra người thật (đợi người dùng bấm nút)
                    if name != "Unknown" and sim > 0.5:
                        h, w = frame.shape[:2]
                        c_top, c_bottom = max(0, top-20), min(h, bottom+20)
                        c_left, c_right = max(0, left-20), min(w, right+20)
                        face_crop = frame[c_top:c_bottom, c_left:c_right]
                        FACE_BUFFER[name] = (current_time, face_crop)

                except Exception as e:
                    continue

        # Dọn dẹp bộ đệm: Xóa những người đã rời khỏi camera quá 3 giây
        keys_to_del = [k for k, v in FACE_BUFFER.items() if current_time - v[0] > 3.0]
        for k in keys_to_del:
            del FACE_BUFFER[k]

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ret: continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# ================= CÁC ENDPOINT API =================

class ActionRequest(BaseModel):
    action: str

@app.post("/api/mark_attendance")
def mark_attendance(req: ActionRequest, username: str = Depends(get_current_user)):
    global FACE_BUFFER
    if not FACE_BUFFER:
        return {"status": "error", "message": "Không thấy ai trong Camera. Vui lòng đứng vào khung hình!"}
    
    recorded = []
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    
    current_time = time.time()
    local_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))
    
    # Duyệt qua các khuôn mặt đang đứng trước cam
    for name, (ts, face_crop) in list(FACE_BUFFER.items()):
        time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(current_time))
        img_filename = f"{name.replace(' ', '_')}_{req.action.replace(' ', '')}_{time_str}.jpg"
        img_path = os.path.join("static/evidence", img_filename)
        
        if face_crop.size > 0:
            cv2.imwrite(img_path, face_crop)
            
        cur.execute("INSERT INTO attendance (name, timestamp, action, image_path) VALUES (?, ?, ?, ?)",
                    (name, local_time, req.action, img_path))
        recorded.append(name)
        
    conn.commit()
    conn.close()
    
    # Xóa đệm để tránh người dùng bấm 2 lần liên tục
    FACE_BUFFER.clear()
    return {"status": "success", "message": f"Đã {req.action} thành công cho: {', '.join(recorded)}"}

@app.get("/api/monthly_report")
def monthly_report(month: str, username: str = Depends(get_current_user)):
    # Trả về tổng số NGÀY đi làm (COUNT DISTINCT date) của từng người trong tháng
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT name, COUNT(DISTINCT date(timestamp)) 
        FROM attendance 
        WHERE strftime('%Y-%m', timestamp) = ?
        GROUP BY name
    """, (month,))
    records = [{"name": row[0], "days": row[1]} for row in cur.fetchall()]
    conn.close()
    return records

@app.post("/api/toggle_camera")
def toggle_camera(username: str = Depends(get_current_user)):
    global is_camera_on
    is_camera_on = not is_camera_on
    return {"status": "success", "is_camera_on": is_camera_on}

@app.get("/api/stats")
def get_stats(username: str = Depends(get_current_user)):
    return system_stats

@app.get("/api/export_csv")
def export_csv(username: str = Depends(get_current_user)):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, timestamp, action, image_path FROM attendance ORDER BY timestamp DESC")
    records = cursor.fetchall()
    conn.close()

    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Họ và Tên", "Thời gian", "Trạng thái", "Đường dẫn ảnh bằng chứng"])
    for row in records:
        writer.writerow(row)

    response = Response(content=stream.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=BaoCao_ChamCong.csv"
    return response

@app.get("/")
async def index(request: Request):
    try:
        session_token = request.cookies.get("session_token")
        if not session_token or session_token not in ACTIVE_SESSIONS:
            return RedirectResponse(url="/login", status_code=303)
        return templates.TemplateResponse(request=request, name="index.html", context={"username": ACTIVE_SESSIONS[session_token]})
    except:
        return RedirectResponse(url="/login", status_code=303)

@app.get("/video_feed")
def video_feed(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token or session_token not in ACTIVE_SESSIONS:
        return HTMLResponse("Unauthorized", status_code=401)
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user[0], user[1]):
        token = secrets.token_hex(32)
        ACTIVE_SESSIONS[token] = username
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session_token", value=token, httponly=True, samesite="strict")
        return response
    return HTMLResponse("<script>alert('Sai tài khoản hoặc mật khẩu!'); window.location='/login';</script>")

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    pwd_hash, salt = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)", 
                       (username, pwd_hash, salt))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return HTMLResponse("<script>alert('Tên tài khoản đã tồn tại!'); window.location='/register';</script>")
    conn.close()
    return HTMLResponse("<script>alert('Đăng ký thành công!'); window.location='/login';</script>")

@app.get("/logout")
def logout(response: Response, request: Request):
    session_token = request.cookies.get("session_token")
    if session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_token]
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)