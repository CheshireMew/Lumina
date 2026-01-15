
Write-Host "🚀 Generating API Client Types..."

$BACKEND_URL = "http://127.0.0.1:8010/openapi.json"
$OUTPUT_FILE = "../app/renderer/src/types/api-schema.d.ts"

# Ensure we are in root or scripts
if (Test-Path "package.json") {
  # Root
} elseif (Test-Path "../package.json") {
  Set-Location ..
}

# Check if Backend is up
try {
    $response = Invoke-WebRequest -Uri $BACKEND_URL -UseBasicParsing -Method Head -ErrorAction Stop
    Write-Host "✅ Backend is online."
} catch {
    Write-Error "❌ Backend not reachable at $BACKEND_URL. Please start the backend first."
    exit 1
}

# Run npx openapi-typescript
# Requires: npm install -D openapi-typescript
Write-Host "📦 Running openapi-typescript..."
if (Test-Path "./node_modules/.bin/openapi-typescript") {
    & ./node_modules/.bin/openapi-typescript $BACKEND_URL -o $OUTPUT_FILE
} else {
    # Try global or npx
    npx openapi-typescript $BACKEND_URL -o $OUTPUT_FILE
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Types generated at $OUTPUT_FILE"
} else {
    Write-Error "❌ Generation failed."
}
