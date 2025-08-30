import asyncio
from datetime import datetime
from typing import List, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, DataTable, Static, TabbedContent, TabPane, TextArea, Button, Input, Label
from textual.reactive import reactive
from textual.screen import ModalScreen
from kubernetes import client, config
from kubernetes.client import ApiException


class K8sAPI:
    def __init__(self):
        try:
            config.load_kube_config()
        except Exception:
            try:
                config.load_incluster_config()
            except Exception as e:
                raise Exception(f"Could not load Kubernetes config: {e}")
        
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def get_pods(self, namespace="default") -> List[Dict[str, Any]]:
        try:
            if namespace == "all":
                pods = self.v1.list_pod_for_all_namespaces()
            else:
                pods = self.v1.list_namespaced_pod(namespace)
            return [
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "ready": f"{sum(1 for c in (pod.status.container_statuses or []) if c.ready)}/{len(pod.spec.containers)}",
                    "restarts": sum(c.restart_count for c in (pod.status.container_statuses or [])),
                    "age": self._calculate_age(pod.metadata.creation_timestamp),
                    "node": pod.spec.node_name or "N/A"
                }
                for pod in pods.items
            ]
        except ApiException as e:
            return []

    def get_nodes(self) -> List[Dict[str, Any]]:
        try:
            nodes = self.v1.list_node()
            return [
                {
                    "name": node.metadata.name,
                    "status": "Ready" if any(c.status == "True" and c.type == "Ready" for c in node.status.conditions) else "NotReady",
                    "roles": ",".join(node.metadata.labels.get("kubernetes.io/role", "worker").split(",")) or "worker",
                    "age": self._calculate_age(node.metadata.creation_timestamp),
                    "version": node.status.node_info.kubelet_version
                }
                for node in nodes.items
            ]
        except ApiException:
            return []

    def get_services(self, namespace="default") -> List[Dict[str, Any]]:
        try:
            if namespace == "all":
                services = self.v1.list_service_for_all_namespaces()
            else:
                services = self.v1.list_namespaced_service(namespace)
            return [
                {
                    "name": svc.metadata.name,
                    "namespace": svc.metadata.namespace,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip or "None",
                    "external_ip": ",".join(svc.status.load_balancer.ingress or []) if svc.status.load_balancer and svc.status.load_balancer.ingress else "None",
                    "ports": ",".join(f"{p.port}:{p.target_port}/{p.protocol}" for p in (svc.spec.ports or [])),
                    "age": self._calculate_age(svc.metadata.creation_timestamp)
                }
                for svc in services.items
            ]
        except ApiException:
            return []

    def get_pod_logs(self, pod_name: str, namespace: str, container: str = None, tail_lines: int = 100, follow: bool = False) -> str:
        try:
            if container:
                logs = self.v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container,
                    tail_lines=tail_lines,
                    follow=follow,
                    timestamps=True
                )
            else:
                logs = self.v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    tail_lines=tail_lines,
                    follow=follow,
                    timestamps=True
                )
            return logs
        except ApiException as e:
            return f"Error retrieving logs: {e}"

    def get_pod_events(self, pod_name: str, namespace: str) -> List[Dict[str, Any]]:
        try:
            events = self.v1.list_namespaced_event(
                namespace=namespace,
                field_selector=f"involvedObject.name={pod_name}"
            )
            return [
                {
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "time": event.first_timestamp or event.event_time,
                    "count": event.count or 1
                }
                for event in events.items
            ]
        except ApiException:
            return []

    def _calculate_age(self, timestamp) -> str:
        if not timestamp:
            return "Unknown"
        age = datetime.now(timestamp.tzinfo) - timestamp
        days = age.days
        hours = age.seconds // 3600
        minutes = (age.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"


class LogViewerScreen(ModalScreen):
    def __init__(self, k8s_api: K8sAPI, pod_name: str, namespace: str):
        super().__init__()
        self.k8s_api = k8s_api
        self.pod_name = pod_name
        self.namespace = namespace

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Logs for {self.pod_name} in {self.namespace}")
            with Horizontal(classes="controls"):
                yield Button("Refresh", id="refresh-logs")
                yield Button("Show Errors Only", id="filter-errors")
                yield Button("Show All", id="show-all")
                yield Button("Close", id="close-logs")
            yield TextArea("Loading logs...", id="log-content", read_only=True)

    def on_mount(self) -> None:
        self.refresh_logs()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-logs":
            self.refresh_logs()
        elif event.button.id == "filter-errors":
            self.filter_errors()
        elif event.button.id == "show-all":
            self.refresh_logs()
        elif event.button.id == "close-logs":
            self.dismiss()

    def refresh_logs(self) -> None:
        log_area = self.query_one("#log-content", TextArea)
        log_area.text = "Loading logs..."
        
        logs = self.k8s_api.get_pod_logs(self.pod_name, self.namespace, tail_lines=500)
        events = self.k8s_api.get_pod_events(self.pod_name, self.namespace)
        
        content = f"=== LOGS ===\n{logs}\n\n"
        
        if events:
            content += "=== EVENTS ===\n"
            for event in events[-10:]:  # Show last 10 events
                time_str = event["time"].strftime("%Y-%m-%d %H:%M:%S") if event["time"] else "Unknown"
                content += f"[{time_str}] {event['type']}: {event['reason']} - {event['message']}\n"
        
        log_area.text = content

    def filter_errors(self) -> None:
        log_area = self.query_one("#log-content", TextArea)
        
        logs = self.k8s_api.get_pod_logs(self.pod_name, self.namespace, tail_lines=500)
        events = self.k8s_api.get_pod_events(self.pod_name, self.namespace)
        
        # Filter logs for error-related content
        error_keywords = ["error", "failed", "exception", "panic", "fatal", "warn", "warning"]
        error_logs = []
        
        for line in logs.split('\n'):
            if any(keyword.lower() in line.lower() for keyword in error_keywords):
                error_logs.append(line)
        
        content = "=== ERROR LOGS ===\n" + '\n'.join(error_logs) + "\n\n"
        
        # Filter events for errors and warnings
        error_events = [e for e in events if e["type"] in ["Warning", "Error"]]
        if error_events:
            content += "=== ERROR EVENTS ===\n"
            for event in error_events[-10:]:
                time_str = event["time"].strftime("%Y-%m-%d %H:%M:%S") if event["time"] else "Unknown"
                content += f"[{time_str}] {event['type']}: {event['reason']} - {event['message']}\n"
        
        log_area.text = content if content.strip() != "=== ERROR LOGS ===" else "No errors found in recent logs"


class PodsTable(DataTable):
    def __init__(self, k8s_api: K8sAPI):
        super().__init__()
        self.k8s_api = k8s_api
        self.add_columns("Name", "Namespace", "Ready", "Status", "Restarts", "Age", "Node")
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.can_focus = True

    def refresh_data(self, namespace="default"):
        self.clear()
        pods = self.k8s_api.get_pods(namespace)
        for pod in pods:
            self.add_row(
                pod["name"],
                pod["namespace"], 
                pod["ready"],
                pod["status"],
                str(pod["restarts"]),
                pod["age"],
                pod["node"]
            )
        # Focus the table and move cursor to first row if data exists
        if self.row_count > 0:
            self.focus()
            self.cursor_coordinate = (0, 0)

    def on_key(self, event) -> None:
        # Handle navigation keys explicitly
        if event.key == "up" or event.key == "k":
            if self.cursor_row is not None and self.cursor_row > 0:
                self.cursor_coordinate = (self.cursor_row - 1, 0)
            event.prevent_default()
        elif event.key == "down" or event.key == "j":
            if self.cursor_row is not None and self.cursor_row < self.row_count - 1:
                self.cursor_coordinate = (self.cursor_row + 1, 0)
            event.prevent_default()
        elif event.key == "l" and self.cursor_row is not None:
            # Get selected pod info
            row_data = self.get_row_at(self.cursor_row)
            if row_data:
                pod_name = str(row_data[0])  # Name column
                namespace = str(row_data[1])  # Namespace column
                log_screen = LogViewerScreen(self.k8s_api, pod_name, namespace)
                self.app.push_screen(log_screen)
        elif event.key == "enter" and self.cursor_row is not None:
            # Same as 'l' key for convenience
            row_data = self.get_row_at(self.cursor_row)
            if row_data:
                pod_name = str(row_data[0])
                namespace = str(row_data[1])
                log_screen = LogViewerScreen(self.k8s_api, pod_name, namespace)
                self.app.push_screen(log_screen)


class NodesTable(DataTable):
    def __init__(self, k8s_api: K8sAPI):
        super().__init__()
        self.k8s_api = k8s_api
        self.add_columns("Name", "Status", "Roles", "Age", "Version")

    def refresh_data(self):
        self.clear()
        nodes = self.k8s_api.get_nodes()
        for node in nodes:
            self.add_row(
                node["name"],
                node["status"],
                node["roles"],
                node["age"],
                node["version"]
            )


class ServicesTable(DataTable):
    def __init__(self, k8s_api: K8sAPI):
        super().__init__()
        self.k8s_api = k8s_api
        self.add_columns("Name", "Namespace", "Type", "Cluster-IP", "External-IP", "Ports", "Age")

    def refresh_data(self, namespace="default"):
        self.clear()
        services = self.k8s_api.get_services(namespace)
        for svc in services:
            self.add_row(
                svc["name"],
                svc["namespace"],
                svc["type"],
                svc["cluster_ip"],
                svc["external_ip"],
                svc["ports"],
                svc["age"]
            )


class K8sMonitorApp(App):
    CSS_PATH = None
    
    def __init__(self, namespace="all"):
        super().__init__()
        self.namespace = namespace
        try:
            self.k8s_api = K8sAPI()
        except Exception as e:
            self.exit(message=f"Failed to connect to Kubernetes: {e}")

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Pods", id="pods-tab"):
                yield PodsTable(self.k8s_api)
            with TabPane("Nodes", id="nodes-tab"):
                yield NodesTable(self.k8s_api)
            with TabPane("Services", id="services-tab"):
                yield ServicesTable(self.k8s_api)
        yield Footer()
        yield Static("↑↓/jk: Navigate | l/Enter: View logs | 1/2/3: Switch tabs | r: Refresh | q: Quit", id="help-text")

    def on_mount(self) -> None:
        self.set_interval(5.0, self.refresh_data)
        self.refresh_data()

    def refresh_data(self) -> None:
        tabs = self.query_one("#tabs")
        current_tab = tabs.active
        
        if current_tab == "pods-tab":
            pods_table = self.query_one(PodsTable)
            pods_table.refresh_data(self.namespace)
        elif current_tab == "nodes-tab":
            nodes_table = self.query_one(NodesTable)
            nodes_table.refresh_data()
        elif current_tab == "services-tab":
            services_table = self.query_one(ServicesTable)
            services_table.refresh_data(self.namespace)

    def on_key(self, event) -> None:
        # Handle tab switching
        if event.key == "1":
            tabs = self.query_one("#tabs")
            tabs.active = "pods-tab"
            self.refresh_data()
        elif event.key == "2":
            tabs = self.query_one("#tabs")
            tabs.active = "nodes-tab"
            self.refresh_data()
        elif event.key == "3":
            tabs = self.query_one("#tabs")
            tabs.active = "services-tab"
            self.refresh_data()
        elif event.key == "r":
            # Manual refresh
            self.refresh_data()

    def on_tabbed_content_tab_activated(self, event) -> None:
        self.refresh_data()


if __name__ == "__main__":
    app = K8sMonitorApp()
    app.run()