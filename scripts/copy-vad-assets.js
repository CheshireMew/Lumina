const fs = require('fs');
const path = require('path');

const filesToCopy = [
    {
        srcDir: path.join(__dirname, '../node_modules/onnxruntime-web/dist'),
        // 仅复制 WASM，MJS 通过 Vite alias 处理
        extensions: ['.wasm']
    },
    {
        srcDir: path.join(__dirname, '../node_modules/@ricky0123/vad-web/dist'),
        extensions: ['.onnx', '.js']
    }
];

const destDir = path.join(__dirname, '../public');

if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
}

console.log('Copying VAD assets to public folder...');

filesToCopy.forEach(group => {
    if (fs.existsSync(group.srcDir)) {
        const allFiles = fs.readdirSync(group.srcDir);

        allFiles.forEach(file => {
            const ext = path.extname(file);
            if (group.extensions.includes(ext)) {
                const srcPath = path.join(group.srcDir, file);
                const destPath = path.join(destDir, file);
                try {
                    fs.copyFileSync(srcPath, destPath);
                    console.log(`Copied: ${file}`);
                } catch (e) {
                    console.error(`Failed to copy ${file}:`, e);
                }
            }
        });
    } else {
        console.error(`Source directory not found: ${group.srcDir}`);
    }
});

console.log('Done.');
