
// 手动 Polyfill，解决第三方库在浏览器环境的兼容性问题
if (typeof window !== 'undefined') {
    if (typeof (window as any).global === 'undefined') {
        (window as any).global = window;
    }

    if (typeof (window as any).exports === 'undefined') {
        (window as any).exports = {};
    }

    // 某些库可能还需要 process
    if (typeof (window as any).process === 'undefined') {
        (window as any).process = { env: {} };
    }
}

export { };
