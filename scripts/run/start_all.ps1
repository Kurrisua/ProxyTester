#!/usr/bin/env pwsh

# 启动所有服务的脚本
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Write-Host "===================================="
Write-Host "代理测试工具启动脚本"
Write-Host "===================================="

# 检查 Node.js 和 npm 是否安装
Write-Host "检查 Node.js 和 npm..."
try {
    $nodeVersion = node --version
    $npmVersion = npm --version
    Write-Host "✓ Node.js 版本: $nodeVersion"
    Write-Host "✓ npm 版本: $npmVersion"
} catch {
    Write-Host "✗ Node.js 未安装，请先安装 Node.js"
    Write-Host "访问 https://nodejs.org/ 下载并安装"
    exit 1
}

# 检查 Python 是否安装
try {
    $pythonVersion = python --version
    Write-Host "✓ Python 版本: $pythonVersion"
} catch {
    Write-Host "✗ Python 未安装，请先安装 Python"
    Write-Host "访问 https://www.python.org/ 下载并安装"
    exit 1
}

# 进入项目目录
Write-Host "进入项目目录..."
Set-Location -Path "$ProjectRoot"

# 检查前端依赖是否安装
if (-not (Test-Path "daili\node_modules")) {
    Write-Host "前端依赖未安装，正在安装..."
    Set-Location -Path "daili"
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ 依赖安装失败"
        exit 1
    }
    Set-Location -Path ".."
    Write-Host "✓ 前端依赖安装成功"
}

# 启动 API 服务器
Write-Host "启动 API 服务器..."
Start-Process -FilePath "python" -ArgumentList "api.py" -WorkingDirectory "$ProjectRoot" -WindowStyle "Normal"

# 等待 API 服务器启动
Write-Host "等待 API 服务器启动..."
Start-Sleep -Seconds 3

# 启动前端开发服务器
Write-Host "启动前端开发服务器..."
Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "$ProjectRoot\daili" -WindowStyle "Normal"

# 等待前端服务器启动
Write-Host "等待前端服务器启动..."
Start-Sleep -Seconds 3

Write-Host "===================================="
Write-Host "服务启动完成！"
Write-Host "===================================="
Write-Host "API 服务器地址: http://localhost:5000"
Write-Host "前端页面地址: http://localhost:3000"
Write-Host ""
Write-Host "按任意键关闭此窗口..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
