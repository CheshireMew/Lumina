# 旧浏览器 VAD 资源归档

这里保存原先位于 `public/` 根目录的浏览器 VAD、ONNX Runtime Web 和 Silero VAD 文件。当前语音输入由独立 STT 工作进程负责，应用代码不再引用这些文件。将它们移出 `public/` 后，Vite 不会在每次构建时复制约 64 MB 的无用资源。

这些文件没有被删除。如果以后恢复浏览器端 VAD，需要先恢复对应代码和许可证说明，再把所需文件移回 `public/`，并同步调整 `package.json` 中的安装内容排除规则。
