import argparse
import sys

def __main__():
    parser = argparse.ArgumentParser(description="Kubernetes Terminal Monitor")
    parser.add_argument("--config", type=str, required=False, help="Kubernetes config file path")
    parser.add_argument("--namespace", type=str, default="all", help="Namespace to monitor (default: all)")
    parser.add_argument("--mode", type=str, choices=["textual", "cli"], default="cli", help="UI mode: textual (interactive) or cli (Rich output)")
    parser.add_argument("--mock", action="store_true", help="Use mock data for demo")
    parser.add_argument("--refresh", type=int, default=5, help="Refresh interval in seconds (0 for single snapshot)")
    args = parser.parse_args()

    if args.mode == "textual":
        try:
            from k8s_monitor import K8sMonitorApp
            app = K8sMonitorApp(namespace=args.namespace)
            app.run()
        except Exception as e:
            print(f"Error starting Textual K8s monitor: {e}")
            print("Try using --mode cli instead")
            exit(1)
    else:
        try:
            from k8s_monitor_cli import main as cli_main
            # Override sys.argv for the CLI version
            cli_args = ["k8s_monitor_cli.py"]
            if args.mock:
                cli_args.append("--mock")
            cli_args.extend(["--refresh", str(args.refresh)])
            
            original_argv = sys.argv
            sys.argv = cli_args
            cli_main()
            sys.argv = original_argv
        except Exception as e:
            print(f"Error starting CLI K8s monitor: {e}")
            exit(1)

if __name__ == "__main__":
    __main__()
