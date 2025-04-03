import { defineConfig } from "vite";
import dts from 'vite-plugin-dts'

export default defineConfig({
  build: {
    minify: 'terser',
    sourcemap: true,
    lib: {
      entry: "index.ts",  // 配置入口文件路径
      name: "@vrrtc/vrcomponents",
      fileName: "index",
      formats: ["es", "umd"], // 打包生成的格式
    },
  },
  plugins: [dts()]
});
