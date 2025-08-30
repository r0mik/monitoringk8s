# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

A Kubernetes terminal monitoring application built with Textual:

- `main.py` - Entry point with CLI argument parsing
- `k8s_monitor.py` - Main terminal UI application with Kubernetes integration
- `requirements.txt` - Python dependencies (textual, kubernetes, rich)

## Architecture

The application uses Textual framework for terminal UI with tabbed interface displaying:
- **Pods tab**: Shows pod status, restarts, resources, age
- **Nodes tab**: Displays cluster nodes with status and versions  
- **Services tab**: Lists services with IPs, ports, and types

The `K8sAPI` class handles Kubernetes client operations using the official Python client. Data refreshes automatically every 5 seconds.

## Commands

- **Install dependencies**: `pip install -r requirements.txt`
- **Run CLI monitor**: `python main.py` (default mode, works in restricted environments)
- **Run interactive UI**: `python main.py --mode textual` (requires proper terminal permissions)
- **Demo mode**: `python main.py --mock` (uses sample data, no K8s cluster needed)
- **Single snapshot**: `python main.py --refresh 0` (one-time display)
- **Live updates**: `python main.py --refresh 5` (refresh every 5 seconds)

## Requirements

- Python 3.8+
- Terminal supporting color and UTF-8
- Valid Kubernetes cluster access (kubeconfig or in-cluster config) OR use `--mock` flag for demo