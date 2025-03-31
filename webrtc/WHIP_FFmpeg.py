import asyncio
import subprocess
import cv2
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCSessionDescription
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WHIP_Publisher")

async def whip_publish_rtp(
    rtp_port=5002,
    whip_url="http://localhost:7777/whip/777",
    camera_index=0,
    width=640,
    height=480,
    fps=30
):
    # 使用VP8编码（兼容性更好）
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-vcodec", "libvpx",           # 改用VP8编码
        "-deadline", "realtime",      # 实时编码模式
        "-cpu-used", "4",             # 快速编码（牺牲质量换速度）
        "-b:v", "1500k",
        "-maxrate", "2000k",
        "-bufsize", "1000k",
        "-f", "rtp",
        "-payload_type", "96",         # 固定Payload Type（与SDP一致）
        "-ssrc", "1",                 # 强制指定SSRC（可选）
        "-rtpflags", "latm",          # 分片模式
        f"rtp://127.0.0.1:{rtp_port}?pkt_size=1200",  # 强制分片大小≤1200
        "-sdp_file", "input.sdp"
    ]

    try:
        # 启动FFmpeg进程
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT  # 捕获FFmpeg日志
        )
        logger.info("FFmpeg进程已启动 (PID: %d)", ffmpeg_process.pid)

        # 初始化摄像头
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开摄像头设备 {camera_index}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        logger.info("摄像头已初始化 (分辨率: %dx%d, 帧率: %d)", width, height, fps)

        # 独立线程处理摄像头帧写入
        def write_frames():
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logger.error("摄像头帧读取失败")
                        break
                    ffmpeg_process.stdin.write(frame.tobytes())
            except Exception as e:
                logger.error("帧写入错误: %s", e)
            finally:
                cap.release()
                ffmpeg_process.stdin.close()
                logger.info("摄像头资源已释放")

        import threading
        writer_thread = threading.Thread(target=write_frames, daemon=True)
        writer_thread.start()
        logger.info("摄像头帧写入线程已启动")

        # 初始化WebRTC连接
        pc = RTCPeerConnection()
        logger.info("WebRTC对等连接已创建")

        # 添加视频收发器
        transceiver = pc.addTransceiver("video", direction="recvonly")
        logger.info("视频收发器已添加 (方向: recvonly)")

        # 生成并发送Offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        logger.info("SDP Offer已生成并设置本地描述:\n%s", offer.sdp)

        # 发送WHIP请求
        async with ClientSession() as session:
            logger.info("正在向WHIP端点发送请求: %s", whip_url)
            async with session.post(
                whip_url,
                data=pc.localDescription.sdp,
                headers={"Content-Type": "application/sdp"}
            ) as response:
                logger.info("收到服务器响应 (状态码: %d)", response.status)
                if response.status != 201:
                    error_detail = await response.text()
                    logger.error("WHIP请求失败: %s", error_detail)
                    raise RuntimeError(f"WHIP推流失败: HTTP {response.status}")
                answer_sdp = await response.text()
                logger.info("SDP Answer接收成功:\n%s", answer_sdp)

        # 处理Answer
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await pc.setRemoteDescription(answer)
        logger.info("远端描述已设置")

        # 保持主线程运行
        logger.info("推流已成功启动，按 Ctrl+C 停止...")
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error("发生未捕获的异常: %s", str(e), exc_info=True)
        raise
    finally:
        # 清理资源
        logger.info("开始清理资源...")
        if 'ffmpeg_process' in locals():
            ffmpeg_process.kill()
            logger.info("FFmpeg进程已终止")
        if 'pc' in locals():
            await pc.close()
            logger.info("WebRTC连接已关闭")

if __name__ == "__main__":
    asyncio.run(whip_publish_rtp(
        whip_url="http://localhost:7777/whip/714",
        camera_index=0,
        width=640,
        height=480,
        fps=30
    ))