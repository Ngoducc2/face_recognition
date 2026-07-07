import cv2
import os
import numpy as np
import warnings
from insightface.app import FaceAnalysis

# Ẩn các cảnh báo không cần thiết từ thư viện cũ nếu có
warnings.filterwarnings("ignore", category=FutureWarning)

class FaceRecognizer:
    def __init__(self, dataset_path="dataset", det_size=(640, 640)):
        print("==> Đang khởi tạo mô hình InsightFace...")
        self.face_app = FaceAnalysis(name='buffalo_l')
        # Tăng det_size lên 640x640 để nhận diện chính xác hơn
        self.face_app.prepare(ctx_id=-1, det_size=det_size)
        
        self.known_embeddings = []
        self.known_face_names = []
        self.dataset_path = dataset_path
        self.load_dataset()

    def load_dataset(self):
        print("==> Đang nạp dữ liệu khuôn mặt từ dataset...")
        if not os.path.exists(self.dataset_path):
            os.makedirs(self.dataset_path)
            print(f"Đã tạo thư mục '{self.dataset_path}'. Hãy thêm ảnh vào và chạy lại!")
            return

        for file_name in os.listdir(self.dataset_path):
            if file_name.endswith((".jpg", ".png", ".jpeg")):
                name = os.path.splitext(file_name)[0].replace("_", " ")
                img_path = os.path.join(self.dataset_path, file_name)
                img = cv2.imread(img_path)
                
                if img is None:
                    print(f"  x Lỗi: Không thể đọc file ảnh {file_name}")
                    continue
                    
                faces = self.face_app.get(img)
                
                if len(faces) > 0:
                    self.known_embeddings.append(faces[0].embedding)
                    self.known_face_names.append(name)
                    print(f"  + Đã nạp thành công: {name}")
                else:
                    print(f"  x Bỏ qua {file_name}: Không tìm thấy khuôn mặt trong ảnh thẻ!")
        print(f"==> Hoàn thành! Đã nạp {len(self.known_face_names)} khuôn mặt.")

    @staticmethod
    def compute_similarity(embedding1, embedding2):
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        return dot_product / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0

    # 1. ĐỔI TÊN HÀM THÀNH 'recognize' ĐỂ KHỚP VỚI main.py
    def recognize(self, frame, threshold=0.45):
        faces = self.face_app.get(frame)
        results = []
        
        for face in faces:
            best_sim = 0.0
            name = "Unknown"
            
            if len(self.known_embeddings) > 0:
                similarities = [self.compute_similarity(face.embedding, emb) for emb in self.known_embeddings]
                best_match_idx = np.argmax(similarities)
                best_sim = similarities[best_match_idx]
                
                if best_sim > threshold:
                    name = self.known_face_names[best_match_idx]
                    
            results.append({
                "bbox": face.bbox.astype(int),
                "name": name,
                "similarity": float(best_sim) # Ép kiểu về float thuần Python cho an toàn dữ liệu
            })
            
        # 2. CHỈ TRẢ VỀ DANH SÁCH 'results' (Dạng Dict đã bóc tách)
        # Bỏ biến 'faces' thừa để vòng lặp bên main.py chạy đúng cấu trúc dữ liệu
        return results