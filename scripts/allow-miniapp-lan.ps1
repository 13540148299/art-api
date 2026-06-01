param(
    [int]$Port = 8000,
    [string]$RuleName = "Art API Dev $Port"
)

$ErrorActionPreference = "Stop"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "请使用以管理员身份运行的 PowerShell 执行本脚本。"
    }
}

function Get-WlanIPv4 {
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.InterfaceAlias -eq "WLAN" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.IPAddress -ne "127.0.0.1"
        } |
        Select-Object -First 1

    if (-not $ip) {
        throw "未找到 WLAN IPv4 地址，请确认电脑和手机已连接到同一 Wi-Fi 或热点。"
    }
    return $ip.IPAddress
}

Assert-Administrator

$profile = Get-NetConnectionProfile -InterfaceAlias "WLAN" -ErrorAction SilentlyContinue
if ($profile -and $profile.NetworkCategory -eq "Public") {
    # 真机联调需要手机访问电脑入站端口，公共网络配置通常会拦截该请求。
    Set-NetConnectionProfile -InterfaceAlias "WLAN" -NetworkCategory Private
}

$existingRule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    New-NetFirewallRule `
        -DisplayName $RuleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $Port `
        -Profile Private,Public | Out-Null
}

$address = Get-WlanIPv4
Write-Host "已放通本机 TCP $Port 入站端口。"
Write-Host "小程序接口地址：http://$address`:$Port/api/v1"
Write-Host "后端启动命令：python -m uvicorn app.main:app --host 0.0.0.0 --port $Port --reload"
Write-Host "请在手机浏览器打开验证：http://$address`:$Port/api/v1/health"
