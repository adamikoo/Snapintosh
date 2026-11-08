# SPDX-License-Identifier: MIT
$vol = Get-Partition -DriveLetter D
$size = $vol.Size
$targetSize = $size - 2147483648 # shrink by 2 GB
Write-Host "Current Size: " ([math]::Round($size / 1GB, 2)) "GB"
Write-Host "Target Size:  " ([math]::Round($targetSize / 1GB, 2)) "GB"
