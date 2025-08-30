#!/usr/bin/env python3

import argparse
import time
from datetime import datetime
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

class MockK8sAPI:
    """Mock K8s API for demonstration when no cluster is available"""
    
    def get_pods(self, namespace="default") -> List[Dict[str, Any]]:
        return [
            {
                "name": "nginx-deployment-7d8cdf8d9c-abc123",
                "namespace": "default",
                "status": "Running",
                "ready": "1/1",
                "restarts": 0,
                "age": "2d",
                "node": "worker-node-1"
            },
            {
                "name": "api-server-78f9cd5b2a-def456",
                "namespace": "default", 
                "status": "Running",
                "ready": "1/1",
                "restarts": 2,
                "age": "1d",
                "node": "worker-node-2"
            },
            {
                "name": "redis-cache-9b8a7c6d5e-ghi789",
                "namespace": "default",
                "status": "Pending",
                "ready": "0/1",
                "restarts": 0,
                "age": "5m",
                "node": "worker-node-1"
            }
        ]

    def get_nodes(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "master-node",
                "status": "Ready",
                "roles": "control-plane,master",
                "age": "30d",
                "version": "v1.28.2"
            },
            {
                "name": "worker-node-1", 
                "status": "Ready",
                "roles": "worker",
                "age": "30d",
                "version": "v1.28.2"
            },
            {
                "name": "worker-node-2",
                "status": "Ready", 
                "roles": "worker",
                "age": "29d",
                "version": "v1.28.2"
            }
        ]

    def get_services(self, namespace="default") -> List[Dict[str, Any]]:
        return [
            {
                "name": "kubernetes",
                "namespace": "default",
                "type": "ClusterIP",
                "cluster_ip": "10.96.0.1",
                "external_ip": "None",
                "ports": "443/TCP",
                "age": "30d"
            },
            {
                "name": "nginx-service",
                "namespace": "default",
                "type": "LoadBalancer", 
                "cluster_ip": "10.96.1.100",
                "external_ip": "203.0.113.42",
                "ports": "80:30080/TCP",
                "age": "2d"
            }
        ]


def create_pods_table(pods: List[Dict[str, Any]]) -> Table:
    table = Table(title="Kubernetes Pods")
    table.add_column("Name", style="cyan")
    table.add_column("Namespace", style="magenta")
    table.add_column("Ready", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Restarts", style="red")
    table.add_column("Age", style="blue")
    table.add_column("Node", style="white")
    
    for pod in pods:
        status_style = "green" if pod["status"] == "Running" else "red"
        table.add_row(
            pod["name"][:30] + ("..." if len(pod["name"]) > 30 else ""),
            pod["namespace"],
            pod["ready"],
            f"[{status_style}]{pod['status']}[/{status_style}]",
            str(pod["restarts"]),
            pod["age"],
            pod["node"]
        )
    return table


def create_nodes_table(nodes: List[Dict[str, Any]]) -> Table:
    table = Table(title="Kubernetes Nodes")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Roles", style="magenta")
    table.add_column("Age", style="blue")
    table.add_column("Version", style="yellow")
    
    for node in nodes:
        status_style = "green" if node["status"] == "Ready" else "red"
        table.add_row(
            node["name"],
            f"[{status_style}]{node['status']}[/{status_style}]",
            node["roles"],
            node["age"],
            node["version"]
        )
    return table


def create_services_table(services: List[Dict[str, Any]]) -> Table:
    table = Table(title="Kubernetes Services")
    table.add_column("Name", style="cyan")
    table.add_column("Namespace", style="magenta")
    table.add_column("Type", style="yellow")
    table.add_column("Cluster-IP", style="green")
    table.add_column("External-IP", style="red")
    table.add_column("Ports", style="blue")
    table.add_column("Age", style="white")
    
    for svc in services:
        table.add_row(
            svc["name"],
            svc["namespace"],
            svc["type"],
            svc["cluster_ip"],
            svc["external_ip"],
            svc["ports"],
            svc["age"]
        )
    return table


def create_dashboard(k8s_api) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(create_pods_table(k8s_api.get_pods()), name="pods"),
        Layout(create_nodes_table(k8s_api.get_nodes()), name="nodes"),
        Layout(create_services_table(k8s_api.get_services()), name="services")
    )
    return layout


def main():
    parser = argparse.ArgumentParser(description="Kubernetes Monitor CLI")
    parser.add_argument("--mock", action="store_true", help="Use mock data for demo")
    parser.add_argument("--refresh", type=int, default=5, help="Refresh interval in seconds")
    args = parser.parse_args()

    console = Console()
    
    if args.mock:
        console.print("[yellow]Running in mock mode - using demo data[/yellow]")
        k8s_api = MockK8sAPI()
    else:
        try:
            from k8s_monitor import K8sAPI
            k8s_api = K8sAPI()
            console.print("[green]Connected to Kubernetes cluster[/green]")
        except Exception as e:
            console.print(f"[red]Failed to connect to Kubernetes: {e}[/red]")
            console.print("[yellow]Falling back to mock mode[/yellow]")
            k8s_api = MockK8sAPI()

    # Single snapshot mode
    if args.refresh == 0:
        dashboard = create_dashboard(k8s_api)
        console.print(Panel(dashboard, title=f"Kubernetes Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        return

    # Live updating mode
    with Live(create_dashboard(k8s_api), refresh_per_second=1/args.refresh) as live:
        try:
            while True:
                time.sleep(args.refresh)
                dashboard = create_dashboard(k8s_api)
                live.update(Panel(dashboard, title=f"Kubernetes Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped by user[/yellow]")


if __name__ == "__main__":
    main()