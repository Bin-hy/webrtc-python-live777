import asyncio
import websockets
import json

clients = {}

async def handle_client(websocket, path):
    try:
        # 接收客户端类型（如 "python" 或 "browser"）
        client_type = await websocket.recv()
        print(f"客户端已连接: {client_type}")
        clients[client_type] = websocket

        async for message in websocket:
            data = json.loads(message)
            print(f"收到来自 {client_type} 的消息: {data}")

            # 转发规则：Python → Browser，Browser → Python
            target = "browser" if client_type == "python" else "python"
            if target in clients:
                await clients[target].send(json.dumps(data))
                print(f"转发消息到 {target}: {data}")
            else:
                print(f"目标客户端 {target} 未连接")

    except websockets.exceptions.ConnectionClosed:
        print(f"客户端 {client_type} 断开连接")
        if client_type in clients:
            del clients[client_type]

async def signal_server():
    async with websockets.serve(handle_client, "0.0.0.0", 1111):
        print("信令服务器已启动，监听端口 1111")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(signal_server())