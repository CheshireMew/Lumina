
Write-Host "🚀 Generating API Client Types..."

$BACKEND_URL = "http://127.0.0.1:8010/openapi.json"
# Path relative to Project Root (CWD will be set to Root)
$OUTPUT_FILE = "app/renderer/api-schema.d.ts" 

if (!(Test-Path "app/renderer/types")) {
    New-Item -ItemType Directory -Force -Path "app/renderer/types" | Out-Null
    $OUTPUT_FILE = "app/renderer/types/api-schema.d.ts"
}
else {
    $OUTPUT_FILE = "app/renderer/types/api-schema.d.ts"
}

# Ensure we are in root or scripts
if (Test-Path "package.json") {
    # Root
}
elseif (Test-Path "../package.json") {
    Set-Location ..
}

# Check if Backend is up
try {
    Invoke-WebRequest -Uri $BACKEND_URL -UseBasicParsing -Method Head -ErrorAction Stop | Out-Null
    Write-Host "✅ Backend is online."
}
catch {
    Write-Error "❌ Backend not reachable at $BACKEND_URL. Please start the backend first."
    exit 1
}

# Run npx openapi-typescript
# Requires: npm install -D openapi-typescript
Write-Host "📦 Running openapi-typescript..."
if (Test-Path "./node_modules/.bin/openapi-typescript") {
    & ./node_modules/.bin/openapi-typescript $BACKEND_URL -o $OUTPUT_FILE
}
else {
    # Try global or npx
    npx openapi-typescript $BACKEND_URL -o $OUTPUT_FILE
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Types generated at $OUTPUT_FILE"
}
else {
    Write-Error "❌ Generation failed."
}
