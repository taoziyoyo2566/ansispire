# Ansispire Project TODO List

## Current Phase: Functional Depth & Stability

### 🟢 Completed Tasks
- establish AI-native governance (GEMINI.md)
- mass quality refactoring (lint clean)
- zero-data-loss audit relay with pagination
- lightweight EDA reaction engine core
- basic Nginx auto-remediation logic (feat/eda-remediation-nginx)

### 🟡 Pending / Future Tasks

#### 🚀 Stability & Infrastructure (Priority 1)
- [TASK-006] **[PENDING] 升级至 Ansible-Core 2.20.5 (2026 LTS)**
    - **Priority**: 0 (Critical)
    - **Description**: 升级核心引擎至 2026 稳定版，锁定 requirements.yml 中的插件版本，彻底消除版本不匹配告警。
- [TASK-004] **[IN_PROGRESS] Robust Bootstrap 2.0**
    - **Current Branch**: `refactor/infra-bootstrap-v2`
    - Description: Create a foolproof initialization script/Makefile target that handles venv, shell path exports, and ANSIBLE_COLLECTIONS_PATH consistency to fix Molecule execution.
- [TASK-005] **Production Deployment Blueprint**
    - Description: Detailed documentation/playbook for deploying the entire system on a clean host.

#### 🛠 Business Logic & Features (Priority 2)
- [TASK-001] **Advanced Self-Healing Scenarios**
    - Description: Expand `rules.json` to handle more complex events (e.g., automated DB failover or disk cleanup).
- [TASK-002] **Monitoring Integration**
    - Description: Export audit and reaction metrics to Prometheus.

#### 🏗 Architecture (Priority 3)
- [TASK-003] **Controller High Availability**
    - Description: Multi-node Semaphore setup.
