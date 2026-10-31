#!/usr/bin/env python3
"""Minimal desktop chat client for a vLLM OpenAI-compatible API."""
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")
DEFAULT_MODEL = os.environ.get("VLLM_MODEL", "local-model")
DEFAULT_API_KEY = os.environ.get("VLLM_API_KEY", "")

class VLLMChatApp:
    """
    A GUI application for interacting with a vLLM (large language model) API.
    
    This class provides a complete chat interface with:
    - Configuration settings for API endpoint, model, and authentication
    - Real-time chat display with message tagging (user/assistant/system/error)
    - Message sending functionality with Ctrl+Enter shortcut
    - Connection testing and chat clearing capabilities
    
    The application uses an OpenAI-compatible API endpoint and supports
    API key authentication for secure communication with the vLLM service.
    
    Key features:
    - Configurable base URL for the vLLM API endpoint
    - Model selection and API key management
    - Rich text display with message type differentiation
    - Error handling for failed API requests
    
    Usage:
    Create an instance of the application with a Tkinter root window:
    app = VLLMChatApp(root)
    app.mainloop()
    """
    def __init__(self, root):
        self.root = root
        self.root.title("vLLM Chat Test")
        self.root.geometry("820x650")
        self.messages = []
        self.busy = False

        settings = ttk.Frame(root, padding=10)
        settings.pack(fill="x")

        ttk.Label(settings, text="Base URL").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        self.url_var = tk.StringVar(value=DEFAULT_BASE_URL)
        ttk.Entry(settings, textvariable=self.url_var, width=44).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(settings, text="Model").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        ttk.Entry(settings, textvariable=self.model_var, width=44).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(settings, text="API Key").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=4)
        self.key_var = tk.StringVar(value=DEFAULT_API_KEY)
        ttk.Entry(settings, textvariable=self.key_var, show="*", width=44).grid(row=2, column=1, sticky="ew", pady=4)

        self.test_btn = ttk.Button(settings, text="Test connection", command=self.test_connection)
        self.test_btn.grid(row=0, column=2, rowspan=2, padx=(10, 0), sticky="ns")
        ttk.Button(settings, text="Clear chat", command=self.clear_chat).grid(row=2, column=2, padx=(10, 0), sticky="ew")
        settings.columnconfigure(1, weight=1)

        self.chat = tk.Text(root, wrap="word", state="disabled", padx=12, pady=12, font=("Sans", 11))
        self.chat.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.chat.tag_configure("user", font=("Sans", 11, "bold"))
        self.chat.tag_configure("assistant", font=("Sans", 11))
        self.chat.tag_configure("system", foreground="#555555", font=("Sans", 9, "italic"))
        self.chat.tag_configure("error", foreground="#b00020")

        bottom = ttk.Frame(root, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        self.input = tk.Text(bottom, height=3, wrap="word", font=("Sans", 11))
        self.input.pack(side="left", fill="both", expand=True)
        self.input.bind("<Control-Return>", self._ctrl_enter)
        self.send_btn = ttk.Button(bottom, text="Send", command=self.send_message)
        self.send_btn.pack(side="left", padx=(8, 0), fill="y")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status_var, anchor="w", padding=(10, 3)).pack(fill="x")

        self.append("System", "API: OpenAI-compatible endpoint. Ctrl+Enter sends a message.", "system")
        self.input.focus_set()

    def _ctrl_enter(self, _event):
        self.send_message()
        return "break"

    def append(self, label, text, tag=None):
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{label}: ", tag or "system")
        self.chat.insert("end", text + "\n\n", tag or "system")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def settings(self):
        base = self.url_var.get().strip().rstrip("/")
        model = self.model_var.get().strip()
        key = self.key_var.get().strip()
        if not base:
            raise ValueError("Base URL cannot be empty.")
        if not model:
            raise ValueError("Model cannot be empty.")
        return base, model, key

    def request_json(self, path, payload=None, timeout=120):
        base, _model, key = self.settings()
        headers = {"Accept": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        req = Request(base + path, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return json.loads(body) if body else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {exc.reason}\n{detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not connect: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("Request timed out.") from exc

    def test_connection(self):
        if self.busy:
            return
        self.busy = True
        self.test_btn.configure(state="disabled")
        self.status_var.set("Testing API...")
        threading.Thread(target=self._test_worker, daemon=True).start()

    def _test_worker(self):
        try:
            result = self.request_json("/models", timeout=15)
            data = result.get("data", [])
            names = [item.get("id", "(unknown)") for item in data]
            self.root.after(0, self._test_done, True, "Connected. Models: " + (", ".join(names) if names else "no models listed"))
        except Exception as exc:
            self.root.after(0, self._test_done, False, str(exc))

    def _test_done(self, ok, text):
        self.busy = False
        self.test_btn.configure(state="normal")
        self.status_var.set("Connection successful" if ok else "Connection failed")
        self.append("Test", text, "system" if ok else "error")
        if not ok:
            messagebox.showerror("vLLM connection failed", text)

    def send_message(self):
        if self.busy:
            return
        text = self.input.get("1.0", "end").strip()
        if not text:
            return
        try:
            base, model, _key = self.settings()
        except Exception as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return
        self.input.delete("1.0", "end")
        self.append("You", text, "user")
        self.messages.append({"role": "user", "content": text})
        self.busy = True
        self.send_btn.configure(state="disabled")
        self.test_btn.configure(state="disabled")
        self.status_var.set("Waiting for vLLM response...")
        threading.Thread(target=self._chat_worker, args=(model, list(self.messages)), daemon=True).start()

    def _chat_worker(self, model, messages):
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 512,
                "stream": False,
            }
            result = self.request_json("/chat/completions", payload=payload, timeout=180)
            choices = result.get("choices", [])
            if not choices:
                raise RuntimeError("API returned no choices:\n" + json.dumps(result, ensure_ascii=False, indent=2))
            answer = choices[0].get("message", {}).get("content", "")
            if isinstance(answer, list):
                answer = "\n".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in answer)
            if not answer:
                answer = "(The model returned an empty response.)"
            self.root.after(0, self._chat_done, True, answer)
        except Exception as exc:
            self.root.after(0, self._chat_done, False, str(exc))

    def _chat_done(self, ok, result):
        self.busy = False
        self.send_btn.configure(state="normal")
        self.test_btn.configure(state="normal")
        if ok:
            self.messages.append({"role": "assistant", "content": result})
            self.append("Assistant", result, "assistant")
            self.status_var.set("Ready")
        else:
            # Remove the failed last user message from conversation history.
            if self.messages and self.messages[-1].get("role") == "user":
                self.messages.pop()
            self.append("Error", result, "error")
            self.status_var.set("Request failed")

    def clear_chat(self):
        if self.busy:
            return
        self.messages.clear()
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self.append("System", "Chat cleared.", "system")

def main():
    root = tk.Tk()
    VLLMChatApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
