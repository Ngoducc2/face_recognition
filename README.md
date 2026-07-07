# face_recognition
face recognition system
Bước 1: Kiểm tra môi trường máy tính
Python: Đảm bảo máy đã cài Python phiên bản từ 3.8 đến 3.11 (InsightFace hoạt động ổn định nhất ở các phiên bản này).

Bước 2: Cài đặt các thư viện bổ sung
Mở Terminal/Command Prompt trong VS Code tại thư mục dự án và chạy lệnh cài đặt tất cả các thư viện cần thiết (ở bản mới này đã bổ sung thêm pydantic để truyền nhận dữ liệu API):

Bash
pip install fastapi uvicorn opencv-python insightface onnxruntime numpy pydantic Jinja2

Bước 3: Sắp xếp cấu trúc thư mục cho đúng
Anh kiểm tra lại xem các file đã nằm đúng vị trí quy định chưa nhé:

Plaintext
Thư mục_Dự_Án/
├── dataset/                # Thư mục chứa ảnh thẻ (Ví dụ: Duc_Ngo.jpg)
├── static/                 # Thư mục chứa file tĩnh
│   └── evidence/           # Hệ thống tự tạo để lưu ảnh chụp lúc bấm nút
├── templates/              # Thư mục chứa giao diện HTML
│   ├── index.html          # File index mới có nút bấm và bảng tra cứu
│   ├── login.html
│   └── register.html
├── face_engine.py          # File xử lý AI
├── main.py                 # File server FastAPI mới
└── README.md

Bước 4: Khởi chạy hệ thống
Tại Terminal của VS Code, anh gõ lệnh sau để kích hoạt Server:

Bash
python main.py
💡 Lưu ý quan trọng cho lần chạy đầu tiên: > Nếu đây là lần đầu tiên anh chạy mô hình buffalo_l, thư viện InsightFace sẽ tự động tải các file model AI từ internet về máy (nặng khoảng 300MB - 500MB). Khung Terminal có thể sẽ tải một thanh Progress Bar hoặc hơi khựng lại một chút. Anh vui lòng đợi vài phút cho đến khi màn hình xuất hiện dòng chữ:
INFO: Uvicorn running on http://127.0.0.1:8000

Bước 5: Quy trình test các tính năng mới trên giao diện
Khi server đã chạy, anh mở trình duyệt web và truy cập: http://127.0.0.1:8000

Đăng ký tài khoản Admin: Hệ thống sẽ tự chuyển hướng anh về trang đăng nhập /login. Anh bấm vào Đăng ký ngay để tạo một tài khoản (Ví dụ: tên admin, mật khẩu 123456). Hệ thống sẽ tự tạo file cơ sở dữ liệu users.db trong thư mục.

Đăng nhập vào Dashboard: Dùng tài khoản vừa tạo để đăng nhập vào. Lúc này camera sẽ bật lên.

Thử nghiệm bấm nút Đi làm / Tan làm:

Anh đứng vào khung hình camera sao cho mô hình nhận diện được khuôn mặt và hiện Khung màu xanh kèm Tên của anh.

Bấm nút 👋 ĐI LÀM hoặc 🏃 TAN LÀM.

Trình duyệt sẽ hiện thông báo: “Đã Đi làm thành công cho: [Tên của anh]”.

Anh có thể kiểm tra trong thư mục static/evidence/ sẽ thấy một file ảnh mới được chụp ngay tại khoảnh khắc anh bấm nút để làm bằng chứng đối chiếu.

Kiểm tra đếm số buổi cuối tháng:

Nhìn sang cột bên phải (bên trên phần biểu đồ hiệu năng), anh sẽ thấy một ô chọn tháng và nút TRA CỨU.

Hệ thống tự động lấy tháng hiện tại làm mặc định. Anh bấm nút TRA CỨU, bảng phía dưới sẽ lập tức hiển thị danh sách nhân sự kèm tổng số ngày đi làm thực tế trong tháng đó (Hệ thống dùng thuật toán lọc trùng ngày COUNT DISTINCT, tức là dù một ngày anh bấm nút Đi làm/Tan làm bao nhiêu lần thì cuối tháng hệ thống vẫn tính chính xác là anh đã đi làm 1 ngày công).
