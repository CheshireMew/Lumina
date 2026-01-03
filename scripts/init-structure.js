const fs = require('fs');
const path = require('path');

const directories = [
  'core/llm',
  'core/memory',
  'core/personality',
  'core/voice',
  'core/context',
  'app/main',
  'app/renderer/components',
  'app/renderer/live2d-view',
  'app/renderer/pages',
  'app/bridge',
  'assets/live2d',
  'assets/icons',
  'assets/sounds',
  'scripts',
  'test',
  'docs'
];

directories.forEach(dir => {
  const fullPath = path.join(process.cwd(), dir);
  if (!fs.existsSync(fullPath)) {
    fs.mkdirSync(fullPath, { recursive: true });
    console.log(`Created directory: ${fullPath}`);
    // Create a .gitkeep to ensure git tracks the directory
    fs.writeFileSync(path.join(fullPath, '.gitkeep'), '');
  }
});
