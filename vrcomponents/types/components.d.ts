import VRRtcComponent from '../model/vr-rtc'

type CustomElement<T extends HTMLElement> = Partial<T & { children?: any } & { style?: any }>;

declare global {
  type VRRtcElement = CustomElement<VRRtcComponent>;
  var VRRtcElement: {
    new(): VRRtcElement;
    prototype: VRRtcElement;
  }
  namespace JSX {
    interface IntrinsicElements {
      ['vr-rtc']: VRRtcElement;
    }
  }
}
