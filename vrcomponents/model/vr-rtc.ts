import { WHEPClient } from '@binbat/whip-whep/whep';

class VRRtcComponent extends HTMLElement {
  private dc: RTCDataChannel | null = null;
  private pc: RTCPeerConnection | null = null; // Added to track the peer connection
  private whepClient: WHEPClient | null = null; // Added to track the WHEP client
  private mediaElements: HTMLMediaElement[] = []; // Added to track created media elements

  private bar: HTMLDivElement;
  private root: ShadowRoot;

  private domWsState: HTMLSpanElement;
  private domPcState: HTMLSpanElement;
  private domDcState: HTMLSpanElement;
  private domGamepadState: HTMLSpanElement;

  constructor() {
    super();
    const template = document.createElement("template");

    this.root = this.attachShadow({ mode: "closed" });

    const buttonStart = document.createElement("button");
    buttonStart.onclick = () => {
      this.handlePlay();
    };
    buttonStart.textContent = "start";

    // Add stop button
    const buttonStop = document.createElement("button");
    buttonStop.onclick = () => {
      this.handleStop();
    };
    buttonStop.textContent = "stop";

    const buttonContainer = document.createElement("div");
    buttonContainer.style.display = "flex";
    buttonContainer.style.gap = "10px";
    buttonContainer.appendChild(buttonStart);
    buttonContainer.appendChild(buttonStop);
    this.root.appendChild(buttonContainer);

    this.bar = document.createElement("div");
    this.bar.style.display = "flex";
    this.bar.style.justifyContent = "space-evenly";
    this.bar.style.columnGap = "1em";
    this.root.appendChild(this.bar);

    this.domWsState = document.createElement("span");
    this.bar.appendChild(this.domWsState);

    this.domPcState = document.createElement("span");
    this.bar.appendChild(this.domPcState);

    this.domDcState = document.createElement("span");
    this.bar.appendChild(this.domDcState);

    this.domGamepadState = document.createElement("span");
    this.bar.appendChild(this.domGamepadState);

    this.webrtcState = "uninit";
    this.dataChannelState = "uninit";

    // const buttonClick = document.createElement("button");
    // buttonClick.textContent = "切换相机模式";
    // buttonClick.addEventListener("click", () => {
    //   this.handleClick();
    // });
    // this.root.appendChild(buttonClick);

    const content = template.content.cloneNode(true);
    this.root.appendChild(content);
  }

  set webrtcState(state: string) {
    this.domPcState.innerText = `webrtc: ${state}`;
  }

  set dataChannelState(state: string) {
    this.domDcState.innerText = `dataChannel: ${state}`;
  }

  get debug(): boolean {
    return !!this.getAttribute("debug");
  }

  get whep(): boolean {
    return !!this.getAttribute("whep");
  }

  get autoplay(): boolean {
    return !!this.getAttribute("autoplay");
  }

  get address(): string {
    return this.getAttribute("address") || "";
  }

  set address(value: string) {
    this.setAttribute("address", value);
  }

  private createPeerConnection(): RTCPeerConnection {
    const pc = new RTCPeerConnection({
      iceServers: [
        {
          urls: ["stun:stun.22333.fun"],
        },
        {
          urls: "turn:turn.22333.fun",
          username: "filegogo",
          credential: "filegogo",
        },
      ],
    });
    this.pc = pc; // Store the peer connection
    
    pc.ontrack = (event) => {
      if (event.track.kind === "audio") {
        const audioElement = document.createElement("audio");
        audioElement.srcObject = event.streams[0];
        audioElement.autoplay = true;
        audioElement.muted = false;
        this.root.appendChild(audioElement);
        this.mediaElements.push(audioElement);
      }
      else if (event.track.kind === "video") {
        const videoElement = document.createElement("video");
        videoElement.srcObject = event.streams[0];
        videoElement.autoplay = true;
        videoElement.muted = false;
        videoElement.style.overflow = "hidden";
        this.root.appendChild(videoElement);
        this.mediaElements.push(videoElement);
      }
    };
    return pc;
  }

  startWHEP() {
    const pc = this.createPeerConnection();
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
    this.whepClient = new WHEPClient();
    this.whepClient.view(pc, this.address);
    this.webrtcState = "connected";
  }

  handleClick() {
    const message = { type: "camera_mode_toggle" };
    this.dc?.send(JSON.stringify(message));
  }

  private handlePlay() {
    this.startWHEP();
  }

  private handleStop() {
    // Stop the WHEP client if it exists
    if (this.whepClient) {
      this.whepClient.stop();
      this.whepClient = null;
    }

    // Close the peer connection if it exists
    if (this.pc) {
      this.pc.close();
      this.pc = null;
    }

    // Remove all media elements
    this.mediaElements.forEach(element => {
      if (element.parentNode === this.root) {
        this.root.removeChild(element);
      }
      // Stop all tracks
      if (element.srcObject) {
        const stream = element.srcObject as MediaStream;
        stream.getTracks().forEach(track => track.stop());
        element.srcObject = null;
      }
    });
    this.mediaElements = [];

    this.webrtcState = "disconnected";
  }

  connectedCallback() {
    console.log("autoplay: ", this.autoplay);
    if (this.autoplay) {
      console.log("autoplay");
      this.handlePlay();
    }
  }
}

customElements.define("vr-rtc", VRRtcComponent);
export default VRRtcComponent;