import asyncio
import random
import subprocess
import cv2
import time
from aiohttp import ClientSession
from aiortc import RTCPeerConnection, RTCSessionDescription
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WHIP_Publisher")


async def whip_publish_rtp(
        rtp_port=5002,
        live777_base_url="http://huai-xhy.site:7777",
        live_stream_id="714",
        camera_index=0,
        width=640,
        height=480,
        fps=30
):
    ffmpeg_process = None
    pc = None
    session_id = None
    whip_url = f"{live777_base_url}/whip/{live_stream_id}" #http://ip:port/whip/stream_id

    try:
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

        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        logger.info("FFmpeg PID: %d", ffmpeg_process.pid)

        cap = cv2.VideoCapture(camera_index) # 开发使用当前摄像头模拟 视频流
        if not cap.isOpened():
            raise RuntimeError(f"摄像头 {camera_index} 打开失败")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        logger.info("摄像头已就绪 (%dx%d @%dfps)", width, height, fps)

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
                if ffmpeg_process.stdin:
                    ffmpeg_process.stdin.close()

        writer_thread = threading.Thread(target=write_frames, daemon=True)
        writer_thread.start()

        pc = RTCPeerConnection()
        transceiver = pc.addTransceiver("video", direction="recvonly")
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        async with ClientSession() as session:
            # 发送WHIP请求创建会话
            async with session.post(
                    whip_url,
                    data=pc.localDescription.sdp,
                    headers={"Content-Type": "application/sdp"}
            ) as response:
                if response.status != 201:
                    error_detail = await response.text()
                    logger.error("WHIP 失败: %s", error_detail)
                    raise RuntimeError(f"HTTP {response.status}")

                # 从Location头提取session_id
                location_header = response.headers.get('Location', '')
                logger.info("Location header: %s", location_header)

                # 使用正则表达式提取session_id
                match = re.search(r'/session/([^/]+)/([^/]+)$', location_header)
                if match:
                    live_stream_id = match.group(1)
                    session_id = match.group(2)
                    logger.info("解析到 Stream ID: %s, Session ID: %s", live_stream_id, session_id)
                else:
                    logger.warning("无法从Location解析Session ID: %s", location_header)

                answer_sdp = await response.text()

        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await pc.setRemoteDescription(answer)

        logger.info("推流成功！")
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error("异常: %s", str(e), exc_info=True)
    finally:
        logger.info("开始清理资源...")

        # 先关闭本地资源
        if ffmpeg_process is not None:
            ffmpeg_process.kill()
            logger.info("FFmpeg进程已终止")
        if pc is not None:
            await pc.close()
            logger.info("WebRTC连接已关闭")

        # 发送DELETE请求通知服务器
        if session_id and live_stream_id:
            delete_url = f"{live777_base_url}/session/{live_stream_id}/{session_id}"
            logger.info("发送DELETE请求到: %s", delete_url)
            try:
                async with ClientSession() as session:
                    async with session.delete(delete_url) as resp:
                        if resp.status == 204:
                            logger.info("成功终止服务器端会话")
                        else:
                            logger.error("DELETE请求失败: HTTP %d", resp.status)
            except Exception as e:
                logger.error("发送DELETE请求时出错: %s", str(e))


if __name__ == "__main__":
    import threading

    asyncio.run(whip_publish_rtp(live_stream_id=random.Random().randint(100000000,999999999)))