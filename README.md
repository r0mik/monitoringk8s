# Kubernetes Terminal Monitor

A terminal-based Kubernetes cluster monitoring application built with Textual framework.

## Features

- **Real-time monitoring** of Kubernetes resources
- **Tabbed interface** with three views:
  - **Pods**: Status, restarts, resource usage, and age
  - **Nodes**: Cluster nodes with status and versions
  - **Services**: Service IPs, ports, and types
- **Multiple modes**: CLI output or interactive terminal UI
- **Demo mode** with mock data for testing without a cluster
- **Auto-refresh** with configurable intervals

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic CLI Mode (Default)
```bash
python main.py
```

### Interactive Terminal UI
```bash
python main.py --mode textual
```

### Demo Mode (No Cluster Required)
```bash
python main.py --mock
```

### Custom Refresh Rate
```bash
python main.py --refresh 5  # Refresh every 5 seconds
python main.py --refresh 0  # Single snapshot
```

## Requirements

- Python 3.8+
- Terminal supporting color and UTF-8
- Valid Kubernetes cluster access (kubeconfig or in-cluster config)
- OR use `--mock` flag for demo without cluster

## Dependencies

- `textual` - Terminal UI framework
- `kubernetes` - Official Kubernetes Python client
- `rich` - Rich text formatting