import cv2

# 替换<interface_name>为实际接口（如eth0）
gst_str = (
    "udpsrc address=230.1.1.1 port=1720 multicast-iface=eth0 ! "
    "application/x-rtp,media=video,encoding-name=H264 ! "
    "rtph264depay ! h264parse ! avdec_h264 ! "
    "videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
)

cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)

while cap.isOpened():
    ret, frame = cap.read()
    if ret:
        cv2.imshow("Dog Stream", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        print("Failed to read frame")
        break

cap.release()
cv2.destroyAllWindows()