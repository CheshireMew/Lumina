import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { app } from 'electron';
import axios from 'axios';

/**
 * Python STT Service Manager
 * 管理 Python 后端进程的启动、监控和关闭
 */
export class PythonSTTService {
    private process: ChildProcess | null = null;
    private port: number = 8765;
    private host: string = '127.0.0.1';
    private isReady: boolean = false;

    /**
     * 启动 Python STT 服务
     */
    public async start(): Promise<void> {
        if (this.process) {
            console.log('[PythonSTT] Service already running');
            return;
        }

        let executable: string;
        let args: string[];
        let cwd: string;

        if (app.isPackaged) {
            // Production: Launch compiled executable
            // Note: PyInstaller 'onedir' creates a folder named lumina_backend
            executable = path.join(process.resourcesPath, 'bin', 'lumina_backend', 'lumina_backend.exe');
            args = ['stt'];
            cwd = path.join(process.resourcesPath, 'bin', 'lumina_backend');
            console.log('[PythonSTT] Launching packaged backend:', executable);
        } else {
            // Development: Use local Python
            const pythonScript = path.join(__dirname, '../../python_backend/stt_server.py');
            // Keep user's specific python path for dev stability
            executable = 'C:\\Users\\Dylan\\AppData\\Local\\Programs\\Python\\Python312\\python.exe';
            args = [pythonScript];
            cwd = path.join(__dirname, '../../python_backend');
            console.log('[PythonSTT] Launching dev backend:', executable, args);
        }

        this.process = spawn(executable, args, {
            cwd: cwd,
            stdio: ['ignore', 'pipe', 'pipe'],
            shell: false, 
            windowsHide: true,
            env: { ...process.env, LITE_MODE: app.isPackaged ? 'true' : 'false' }
        });

        // 监听输出
        this.process.stdout?.on('data', (data) => {
            const message = data.toString().trim();
            console.log(`[PythonSTT] ${message}`);

            // 检测服务就绪
            if (message.includes('Application startup complete')) {
                this.isReady = true;
                console.log('[PythonSTT] Service is ready');
            }
        });

        this.process.stderr?.on('data', (data) => {
            console.error(`[PythonSTT] ERROR: ${data.toString().trim()}`);
            // 有些库（如 uvicorn）会把 INFO 级别的日志也输出到 stderr
            if (data.toString().includes('Application startup complete')) {
                this.isReady = true;
                console.log('[PythonSTT] Service is ready (detected via stderr)');
            }
        });

        this.process.on('error', (error) => {
            console.error('[PythonSTT] Process error:', error);
        });

        this.process.on('exit', (code) => {
            console.log(`[PythonSTT] Process exited with code ${code}`);
            this.process = null;
            this.isReady = false;
        });

        // 等待服务启动
        await this.waitForReady();
    }

    /**
     * 等待服务就绪
     */
    private async waitForReady(maxRetries: number = 30): Promise<void> {
        for (let i = 0; i < maxRetries; i++) {
            try {
                const response = await axios.get(`http://${this.host}:${this.port}/health`, {
                    timeout: 1000
                });
                if (response.data.status === 'ok') {
                    this.isReady = true;
                    console.log('[PythonSTT] Health check passed');
                    return;
                }
            } catch (error) {
                // 服务还未就绪，继续等待
            }

            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        throw new Error('Python STT service failed to start within timeout');
    }

    /**
     * 停止服务
     */
    public stop(): void {
        if (this.process) {
            console.log('[PythonSTT] Stopping service...');
            // 使用 tree-kill 或者 taskkill 可能更可靠，但简单场景下 kill 也可以
            // 在 shell: true 模式下，this.process.kill() 可能无法杀死子进程树
            // 这里我们尝试粗暴一点的方式，如果需要的话
            try {
                process.kill(this.process.pid!);
            } catch (e) {
                // Ignore
            }
            this.process = null;
            this.isReady = false;
        }
    }

    /**
     * 获取 WebSocket URL
     */
    public getWebSocketURL(): string {
        return `ws://${this.host}:${this.port}/ws/stt`;
    }

    /**
     * 检查服务是否就绪
     */
    public isServiceReady(): boolean {
        return this.isReady;
    }
}

// 导出单例
export const pythonSTTService = new PythonSTTService();
