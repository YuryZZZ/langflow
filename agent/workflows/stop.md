---
description: STOP & KILL - Isolated Project Termination
---

# STOP & KILL (Isolated)

This command will backup your work and then terminate all processes (CLI and Workers) specifically for this project.

1. Backup artifacts.
2. Run stop.bat (Isolated Termination).

// turbo-all

1. Run command: `echo [SAVING] Backing up artifacts... & if exist ".ai\artifacts" xcopy /E /I /Y ".ai\artifacts" "backup_artifacts" >nul`
2. Run command: `if exist "stop.bat" (stop.bat) else (echo [ERROR] stop.bat not found. Please run oc.bat first to sync.)`
