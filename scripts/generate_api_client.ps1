
Write-Host "Generating API client types..."

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

$SCHEMA_FILE = "Lumina_Data/cache/openapi.json"
python scripts/export_openapi.py $SCHEMA_FILE
if ($LASTEXITCODE -ne 0) {
    Write-Error "OpenAPI export failed."
    exit 1
}

# Run npx openapi-typescript
# Requires: npm install -D openapi-typescript
Write-Host "Running openapi-typescript..."
if (Test-Path "./node_modules/.bin/openapi-typescript") {
    & ./node_modules/.bin/openapi-typescript $SCHEMA_FILE -o $OUTPUT_FILE
}
else {
    Write-Error "openapi-typescript is not installed. Run npm install first."
    exit 1
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Types generated at $OUTPUT_FILE"
}
else {
    Write-Error "Generation failed."
    exit 1
}
