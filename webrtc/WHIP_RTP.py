import cv2
import subprocess


if __name__ == '__main__':
    # 摄像头参数
    CAMERA_INDEX = 0  # 通常为 0 或 /dev/video0
    WIDTH = 1080
    HEIGHT = 720
    FPS = 30
    RTP_PORT = 5002
    WHIP_SERVER_URL = "http://huai-xhy.site:7777/whip/777"

    # 启动 FFmpeg 进程（编码为 H.264/RTP）
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",  # 输入格式为原始视频
        "-vcodec", "rawvideo",  # 原始视频编码
        "-pix_fmt", "bgr24",  # OpenCV 的帧格式为 BGR24
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",  # 从标准输入读取数据
        "-vcodec", "libx264",
        "-profile:v", "baseline",
        "-tune", "zerolatency",
        "-f", "rtp",  # 输出为 RTP 流
        f"rtp://127.0.0.1:{RTP_PORT}",
        "-sdp_file", "input.sdp",
        "-profile:v", "high",  # 使用 high 配置文件
        "-pix_fmt", "yuv420p",
    ]

    # 启动 FFmpeg 进程
    ffmpeg_process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE  # 允许通过管道输入数据
    )

    # 使用 OpenCV 捕获摄像头并推送帧到 FFmpeg
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # 将帧写入 FFmpeg 的标准输入
            ffmpeg_process.stdin.write(frame.tobytes())
    except Exception as e:
        print(f"错误: {e}")
    finally:
        cap.release()
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()

    # 使用 whipinto 将 RTP 流转发到 WHIP
    subprocess.run(["whipinto", "-i", "input.sdp", "-w", WHIP_SERVER_URL])