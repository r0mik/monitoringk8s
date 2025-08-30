#!/usr/bin/env python3

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class SimpleApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Hello, Textual!", id="hello")
        yield Footer()

if __name__ == "__main__":
    app = SimpleApp()
    print("Starting simple Textual app test...")
    try:
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        print("Terminal permissions might be restricted in this environment.")