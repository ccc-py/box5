# Kubernetes (K8s) — 容器編排平台

## 概述

Kubernetes（常簡寫為 K8s，因為 K 與 s 之間有 8 個字母）是一個開放原始碼的容器編排（orchestration）平台，由 Google 設計並捐贈給 CNCF（Cloud Native Computing Foundation）。Kubernetes 負責自動化容器化應用程式的部署、擴展與管理。

**重要區別**：本專案的 k8s/ 目錄雖然名稱源自 Kubernetes，但實際上**並未使用真正的 Kubernetes**。本專案的 k8s/ 只是借用 K8s 的概念，使用 Docker 來實現多租戶容器隔離。真正的 Kubernetes 比本專案的實作複雜得多。

## 核心概念

### Pod

Pod 是 Kubernetes 中最小的部署單元，代表一個或多個容器的集合。Pod 中的容器共享網路命名空間（相同的 IP 與連接埠範圍）與儲存卷（Volume）。

不同於 Docker 直接管理容器，Kubernetes 管理的是 Pod。一個 Pod 通常包含一個主要容器，有時會包含輔助的 sidecar 容器。

### Node

Node（節點）是 Kubernetes 叢集中的工作機器，可以是實體機或虛擬機。每個 Node 上運行著：

- **kubelet**：負責與控制平面通訊，管理 Pod 的生命週期
- **kube-proxy**：負責網路代理與負載平衡
- **Container Runtime**：實際執行容器的軟體（如 Docker、containerd）

### 控制平面（Control Plane）

控制平面負責管理整個叢集的狀態，包含：

- **kube-apiserver**：所有元件的通訊中樞，提供 REST API
- **etcd**：分散式鍵值儲存，儲存叢集的所有設定與狀態
- **kube-scheduler**：負責將 Pod 排程到合適的 Node
- **kube-controller-manager**：執行各種控制器（如 ReplicaSet、Deployment 控制器）

### Deployment

Deployment 是 Kubernetes 中用來管理無狀態應用程式的資源物件，提供：

- **宣告式更新（Declarative Update）**：描述想要的狀態，Kubernetes 自動達成
- **滾動更新（Rolling Update）**：逐步替換舊版本 Pod，確保服務不中斷
- **回滾（Rollback）**：若更新失敗，可快速恢復到之前的版本

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: box5-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: box5
  template:
    metadata:
      labels:
        app: box5
    spec:
      containers:
      - name: box5
        image: box5-server:latest
        ports:
        - containerPort: 3111
```

### Service

Service 提供穩定的網路端點來存取一群 Pod。由於 Pod 的 IP 會動態變化，Service 透過 Label Selector 來找到對應的 Pod，並提供負載平衡。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: box5-service
spec:
  selector:
    app: box5
  ports:
  - port: 80
    targetPort: 3111
  type: ClusterIP
```

Service 的類型：

- **ClusterIP**（預設）：僅叢集內部可存取
- **NodePort**：每個 Node 的特定連接埠對外服務
- **LoadBalancer**：透過雲端平台的負載平衡器對外服務
- **Ingress**：提供 HTTP/HTTPS 路由規則

## 架構示意

```
┌─────────────────────────────────────────────────────┐
│                   Control Plane                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ API Server│  │ Scheduler│  │ Controller Manager│  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │                    etcd                        │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        │
    ┌───────────────────┼───────────────────┐
    ▼                   ▼                   ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│  Node 1  │      │  Node 2  │      │  Node 3  │
│          │      │          │      │          │
│ ┌──────┐ │      │ ┌──────┐ │      │ ┌──────┐ │
│ │ Pod  │ │      │ │ Pod  │ │      │ │ Pod  │ │
│ └──────┘ │      │ └──────┘ │      │ └──────┘ │
│ ┌──────┐ │      │ ┌──────┐ │      │ ┌──────┐ │
│ │ Pod  │ │      │ │ Pod  │ │      │ │ Pod  │ │
│ └──────┘ │      │ └──────┘ │      │ └──────┘ │
└──────────┘      └──────────┘      └──────────┘
```

## 核心功能

### 自動擴展（Auto Scaling）

Kubernetes 可以根據 CPU 使用率或自訂指標自動調整 Pod 的數量：

- **Horizontal Pod Autoscaler (HPA)**：水平擴展（增加/減少 Pod 數量）
- **Vertical Pod Autoscaler (VPA)**：垂直擴展（調整 Pod 的資源請求）
- **Cluster Autoscaler**：自動增減 Node 數量

### 自我修復（Self Healing）

- 若 Pod 崩潰，ReplicaSet 會自動建立新的 Pod
- 若 Node 故障，該 Node 上的 Pod 會被重新排程到其他 Node
- 若容器健康檢查（Liveness Probe）失敗，Kubelet 會重啟容器

### 服務發現（Service Discovery）

Kubernetes 提供內建的 DNS 服務，Pod 可以透過 Service 名稱來存取其他服務。例如，`box5-service.default.svc.cluster.local` 可以解析到對應的 Service IP。

### 配置管理

- **ConfigMap**：儲存非機密性的設定（如設定檔）
- **Secret**：儲存機密性資料（如密碼、API 金鑰），以 base64 編碼儲存

## 與 Docker 的比較

| 特性 | Docker | Kubernetes |
|------|--------|------------|
| 管理單位 | 單一容器 | Pod（一群容器） |
| 叢集管理 | 不支援（需 Docker Swarm） | 原生支援 |
| 自動擴展 | 不支援 | 支援（HPA） |
| 自我修復 | 僅 `--restart` | 完整的健康檢查與重啟 |
| 服務發現 | 需手動設定 | 內建 DNS |
| 負載平衡 | 需手動設定 | 內建 Service |
| 滾動更新 | 不支援 | 支援 |
| 複雜度 | 低 | 高 |

## 本專案的 k8s/ 目錄

本專案的 k8s/ 目錄實作了類似 Kubernetes 的多租戶概念，但技術上只使用 Docker：

- **多租戶**：每個使用者一個 Docker 容器（類似 Pod）
- **資源隔離**：透過 Docker 的命名空間隔離
- **Volume Mount**：類似 Kubernetes 的 PersistentVolumeClaim
- **API 代理**：k8s/main.py 扮演類似 API Gateway 的角色

真正的 Kubernetes 部署需要 YAML 設定檔、kubectl 工具、以及一個 Kubernetes 叢集（如 minikube、kind 或雲端服務商的托管 K8s）。

## 為何使用 K8s 名稱

本專案的 k8s/ 命名可能造成混淆，但反映了其設計目標：未來若需要真正的 Kubernetes 部署，k8s/ 的架構（多租戶、容器隔離、API 代理）可以平滑遷移到真正的 Kubernetes。

## 學習資源

- [Kubernetes 官方文件](https://kubernetes.io/docs/)
- [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
- [Minikube](https://minikube.sigs.k8s.io/) — 在本機執行 Kubernetes
