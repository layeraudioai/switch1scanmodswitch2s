@echo off
cls
set /P roms=Enter full ROM path(s) space delimited: 
for %%A in (%roms%) do (
    echo File name and extension: %%~nxA
    robocopy /e "HBLauncher\apps\gb2ns2" "HBLauncher\apps\%%~nxA"
    cd /d "HBLauncher\apps\%%~nxA"
    echo "%%A"
pause
    node build.cjs "%%A"
    echo %%~nxA is now in HBLauncher apps
)
pause
