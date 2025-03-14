import asyncio
import subprocess
import cv2
import time
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCSessionDescription
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WHIP_Publisher")

async def whip_publish_rtp(
    rtp_port=5002,
    whip_url="http://huai-xhy.site:7777/whip/cv",
    camera_index=0,
    width=640,
    height=480,
    fps=30
):
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-vcodec", "libvpx",
        "-deadline", "realtime",
        "-cpu-used", "8",
        "-b:v", "1M",
        "-maxrate", "1.5M",
        "-bufsize", "500k",
        "-rtbufsize", "256k",
        "-f", "rtp",
        "-flush_packets", "1",
        "-pkt_size", "1200",
        f"rtp://127.0.0.1:{rtp_port}",
        "-sdp_file", "input.sdp"
    ]

    try:
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        logger.info("FFmpeg PID: %d", ffmpeg_process.pid)

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"摄像头 {camera_index} 打开失败")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        logger.info("摄像头已就绪 (%dx%d @%dfps)", width, height, fps)

        # 插入 SDP 时间戳参数
        with open("input.sdp", "a") as f:
            f.write("a=ts-refclk:ptp=IEEE1589-2008\n")
            f.write("a=mediaclk:direct=0\n")

        def write_frames():
            frame_interval = 1.0 / fps
            try:
                while True:
                    start_time = time.time()
                    ret, frame = cap.read()
                    if not ret:
                        break
                    ffmpeg_process.stdin.write(frame.tobytes())
                    elapsed = time.time() - start_time
                    time.sleep(max(0, frame_interval - elapsed))
            except Exception as e:
                logger.error("写入错误: %s", e)
            finally:
                cap.release()
                ffmpeg_process.stdin.close()

        import threading
        writer_thread = threading.Thread(target=write_frames, daemon=True)
        writer_thread.start()

        pc = RTCPeerConnection()
        transceiver = pc.addTransceiver("video", direction="recvonly")
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        async with ClientSession() as session:
            async with session.post(
                whip_url,
                data=pc.localDescription.sdp,
                headers={"Content-Type": "application/sdp"}
            ) as response:
                if response.status != 201:
                    error_detail = await response.text()
                    logger.error("WHIP 失败: %s", error_detail)
                    raise RuntimeError(f"HTTP {response.status}")
                answer_sdp = await response.text()

        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await pc.setRemoteDescription(answer)

        logger.info("推流成功！")
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error("异常: %s", str(e), exc_info=True)
    finally:
        ffmpeg_process.kill()
        await pc.close()
        if 'pc' in locals():
            await pc.close()
            logger.info("WebRTC连接已关闭")
if __name__ == "__main__":
    asyncio.run(whip_publish_rtp())