# python 推流
## aiortc 推流
aiortc捕获默认摄像机1的视频流，推流到自己的sfu服务器，在下面SFU服务器讲到。
```bash
robot env

uv venv --python 3.12
source .venv/bin/activate #  激活虚拟环境
uv pip install -r ./requirements
```
在main中有默认的方案
# SFU服务器 
运行 包 webrtc 下的 main函数,推流到live777服务器，需要自己搭建 [live777](https://github.com/binbat/live777)
live777在本地或者自己的服务器运行
[![live777官方](https://github.com/binbat/live777/blob/main/web/public/logo.svg)](https://github.com/binbat/live777)
## docker 运行live777
```cmd
cd ./dockers/live777
docker compose up -d
```
live777默认在 ip+7777端口上 ,把这个 ip+端口 传递给main的 live777_base_url
本人已经搭建了一个临时的 live777 ，可以尝试使用，可能服务器没了哈哈哈（只租了很短的服务器）
## 推流
设置好了main的 live777 服务器ip后，运行ICE completed 后说明推流成功了！
如果不成功请确认一下是否改动了live777的配置，也就是 dockers/live777/conf/live777.toml ， 里面有stun服务器和turn服务器配置

# 视频观看
可以直接在live777 中观看 ，也可以在 我编写好的观影web 观看
## live777 直接观看
选中你的视频流，点击preview 后观看

## web观看
运行前端界面
```commandline
cd ./web
npm install
npm run dev
```
1. 填写自己的 live777 服务器地址
2. 可以选择查看房间，选中房间
3. 点击start（点一下就行）

### 跨域问题
如果没有画面，出现跨域问题，可能是你修改了 live777 的配置 要设置 cors 为true （默认修改了），运行跨域


