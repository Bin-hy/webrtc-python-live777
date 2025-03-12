import cv2

if __name__ == '__main__':
    # 打开默认摄像头（通常索引为0）
    cap = cv2.VideoCapture(0)

    # 设置分辨率（可选）
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while cap.isOpened():
        ret, frame = cap.read()
        if ret:
            cv2.imshow("Local Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Failed to read frame")
            break
    cap.release()
    cv2.destroyAllWindows()