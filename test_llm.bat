@echo off
echo ========================================
echo   LLM Request Test Script
echo ========================================
echo.
echo Running TypeScript test file...
echo.

npx tsx core/llm/test_llm_request.ts

echo.
echo ========================================
echo   Test Complete!
echo ========================================
pause
