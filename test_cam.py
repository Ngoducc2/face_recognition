import cv2
cap = cv2.VideoCapture(1) # Thử đổi số 0 thành số 1 nếu máy bạn có nhiều camera
if not cap.isOpened():
    print("LỖI: Không thể kết nối với Camera!")
else:
    print("THÀNH CÔNG: Camera hoạt động tốt!")
    ret, frame = cap.read()
    cv2.imshow('Test', frame)
    cv2.waitKey(3000) # Hiện camera 3 giây rồi tự tắt
cap.release()
cv2.destroyAllWindows()