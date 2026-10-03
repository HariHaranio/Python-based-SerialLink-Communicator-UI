import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import time

# --- Performance & Safety Limits ---
MAX_LOG_LINES = 2000         # Maximum lines kept in terminal to prevent OOM / freezing
MAX_LINES_PER_UPDATE = 50    # Max lines rendered per GUI tick to maintain 60 FPS
MAX_QUEUE_SIZE = 2000        # Prevents memory ballooning during high baud-rate data flood

class SerialGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SerialLink Communicator UI")
        self.root.geometry("820x540")

        self.is_resizable = False
        self.root.resizable(False, False)

        # Handle window close button 'X'
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Concurrency & Serial Management
        self.serial_port = None
        self.serial_thread = None
        self.serial_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        
        # State Flags
        self.is_running = True
        self.show_timestamp = True
        self.after_id = None

        self.setup_widgets()
        self.update_ports()
        self.schedule_queue_processing()

    def setup_widgets(self):
        # 1. Serial Connection Frame
        frame_top = ttk.LabelFrame(self.root, text="Serial Connection")
        frame_top.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_top, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_cb = ttk.Combobox(frame_top, state="readonly", width=12)
        self.port_cb.grid(row=0, column=1, padx=5, pady=5)

        self.refresh_btn = ttk.Button(frame_top, text="Refresh", command=self.update_ports)
        self.refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(frame_top, text="Baud Rate:").grid(row=0, column=3, padx=5, pady=5)
        self.baud_cb = ttk.Combobox(
            frame_top,
            values=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"],
            state="readonly",
            width=10
        )
        self.baud_cb.set("115200")
        self.baud_cb.grid(row=0, column=4, padx=5, pady=5)

        self.status_color = tk.Canvas(frame_top, width=20, height=20, highlightthickness=0)
        self.status_circle = self.status_color.create_oval(3, 3, 17, 17, fill="red")
        self.status_color.grid(row=0, column=5, padx=5, pady=5)

        self.connect_btn = ttk.Button(frame_top, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=6, padx=5, pady=5)

        # Spacer column
        frame_top.grid_columnconfigure(7, weight=1)

        self.toggle_resize_btn = ttk.Button(frame_top, text="Enable Resize", command=self.toggle_resize)
        self.toggle_resize_btn.grid(row=0, column=8, padx=5, pady=5)

        self.exit_btn = ttk.Button(frame_top, text="Exit", command=self.exit_app)
        self.exit_btn.grid(row=0, column=9, padx=5, pady=5)

        # 2. Send Data Frame
        frame_send = ttk.LabelFrame(self.root, text="Send Data")
        frame_send.pack(fill="x", padx=10, pady=5)

        self.send_entry = ttk.Entry(frame_send)
        self.send_entry.pack(side="left", padx=5, pady=5, expand=True, fill="x")
        self.send_entry.bind("<Return>", lambda e: self.send_text())

        ttk.Label(frame_send, text="Ending:").pack(side="left", padx=(5, 2))
        self.line_ending_cb = ttk.Combobox(frame_send, values=["\\r\\n", "\\n", "None"], state="readonly", width=6)
        self.line_ending_cb.set("\\r\\n")
        self.line_ending_cb.pack(side="left", padx=(0, 5))

        self.send_btn = ttk.Button(frame_send, text="Send", command=self.send_text)
        self.send_btn.pack(side="right", padx=5, pady=5)

        # 3. Middle Controls Frame
        frame_center = ttk.Frame(self.root)
        frame_center.pack(fill="x", padx=10, pady=3)

        self.clear_btn = ttk.Button(frame_center, text="Clear Terminal", command=self.clear_log)
        self.clear_btn.pack(side=tk.LEFT)

        self.last_sent_label = ttk.Label(frame_center, text="Last sent: -")
        self.last_sent_label.pack(side=tk.LEFT, padx=15)

        self.toggle_time_btn = ttk.Button(frame_center, text="Hide Timestamps", command=self.toggle_timestamp)
        self.toggle_time_btn.pack(side=tk.RIGHT)

        # 4. Terminal / Log Frame with Scrollbar
        frame_log = ttk.LabelFrame(self.root, text="Serial Terminal")
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(frame_log)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            frame_log,
            state="disabled",
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="white",
            padx=6,
            pady=6
        )
        self.log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

    def toggle_resize(self):
        self.is_resizable = not self.is_resizable
        self.root.resizable(self.is_resizable, self.is_resizable)
        self.toggle_resize_btn.config(text="Disable Resize" if self.is_resizable else "Enable Resize")

    def update_ports(self):
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
        except Exception:
            ports = []

        self.port_cb["values"] = ports
        if ports:
            current_val = self.port_cb.get()
            if not current_val or current_val not in ports:
                self.port_cb.set(ports[0])
        else:
            self.port_cb.set("")

    def toggle_connection(self):
        with self.serial_lock:
            is_open = self.serial_port is not None and self.serial_port.is_open
        if is_open:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        port = self.port_cb.get().strip()
        if not port:
            messagebox.showwarning("No Port", "Please select or refresh available COM ports.")
            return

        try:
            baud = int(self.baud_cb.get())
            with self.serial_lock:
                self.serial_port = serial.Serial(port, baud, timeout=0.5)
            
            self.stop_event.clear()
            self.serial_thread = threading.Thread(target=self.read_serial, daemon=True)
            self.serial_thread.start()

            self.connect_btn.config(text="Disconnect")
            self.status_color.itemconfig(self.status_circle, fill="#00FF00")
            self.append_log(f"[System] Connected to {port} at {baud} baud.")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to {port}:\n{e}")

    def disconnect_serial(self):
        # 1. Signal background thread to stop
        self.stop_event.set()

        # 2. Safely close port under lock
        with self.serial_lock:
            if self.serial_port:
                try:
                    self.serial_port.close()
                except Exception:
                    pass
                self.serial_port = None

        # 3. Join thread if not calling from the reader thread itself
        if self.serial_thread and self.serial_thread.is_alive():
            if threading.current_thread() != self.serial_thread:
                self.serial_thread.join(timeout=0.3)
        self.serial_thread = None

        # 4. Safely update UI
        if self.root.winfo_exists():
            self.connect_btn.config(text="Connect")
            self.status_color.itemconfig(self.status_circle, fill="red")
            self.append_log("[System] Disconnected.")

    def read_serial(self):
        """Worker thread for background reading without GUI lockups."""
        while not self.stop_event.is_set():
            try:
                with self.serial_lock:
                    port = self.serial_port
                    if not port or not port.is_open:
                        break
                    in_waiting = port.in_waiting

                if in_waiting > 0:
                    raw_data = port.readline()
                    if raw_data:
                        line = raw_data.decode('utf-8', errors='replace').strip()
                        line = line.replace('\x00', '')  # Remove null characters
                        if line:
                            try:
                                self.queue.put(line, timeout=0.01)
                            except queue.Full:
                                pass  # Drop oldest if queue is flooded
                else:
                    # Interruptible sleep
                    self.stop_event.wait(0.01)

            except Exception:
                if not self.stop_event.is_set():
                    try:
                        self.queue.put("[Warning] Device disconnected or read error.")
                    except queue.Full:
                        pass
                    # Safely dispatch UI cleanup to main thread
                    if self.root.winfo_exists():
                        self.root.after(0, self.disconnect_serial)
                break

    def schedule_queue_processing(self):
        """Processes messages from queue in batches to guarantee responsive UI."""
        if not self.is_running or not self.root.winfo_exists():
            return

        batch = []
        count = 0
        while not self.queue.empty() and count < MAX_LINES_PER_UPDATE:
            try:
                line = self.queue.get_nowait()
                timestamp = time.strftime("[%H:%M:%S] ") if self.show_timestamp else ""
                batch.append(f"{timestamp}[Recv] {line}\n")
                count += 1
            except queue.Empty:
                break

        if batch:
            self.append_batch(batch)

        # Reschedule next check
        if self.is_running and self.root.winfo_exists():
            self.after_id = self.root.after(40, self.schedule_queue_processing)

    def append_batch(self, lines):
        """Batch inserts text and trims old history to prevent memory leaks and UI lag."""
        try:
            self.log_text.config(state="normal")
            self.log_text.insert("end", "".join(lines))

            # Trim excess lines if buffer exceeds limit
            total_lines = int(float(self.log_text.index("end-1c")))
            if total_lines > MAX_LOG_LINES:
                excess = total_lines - MAX_LOG_LINES
                self.log_text.delete("1.0", f"{excess + 1}.0")

            self.log_text.see("end")
            self.log_text.config(state="disabled")
        except tk.TclError:
            pass

    def append_log(self, message):
        """Appends a single status message safely."""
        self.append_batch([message + "\n"])

    def clear_log(self):
        try:
            self.log_text.config(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.config(state="disabled")
        except tk.TclError:
            pass

    def toggle_timestamp(self):
        self.show_timestamp = not self.show_timestamp
        self.toggle_time_btn.config(text="Hide Timestamps" if self.show_timestamp else "Show Timestamps")

    def send_text(self):
        with self.serial_lock:
            port = self.serial_port
            is_open = port is not None and port.is_open

        if not is_open:
            messagebox.showwarning("Not Connected", "Please connect to a serial device first.")
            return

        text = self.send_entry.get()
        if not text:
            return

        ending = self.line_ending_cb.get()
        payload = text
        if ending == "\\r\\n":
            payload += "\r\n"
        elif ending == "\\n":
            payload += "\n"

        try:
            with self.serial_lock:
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.write(payload.encode('utf-8'))
                else:
                    raise serial.SerialException("Port closed during send.")

            self.last_sent_label.config(text=f"Last sent: {text}")
            timestamp = time.strftime("[%H:%M:%S] ") if self.show_timestamp else ""
            self.append_log(f"{timestamp}[Sent] {text}")
            self.send_entry.delete(0, "end")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send data:\n{e}")

    def exit_app(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.is_running = False
            self.stop_event.set()

            # Cancel scheduled GUI updates
            if self.after_id:
                try:
                    self.root.after_cancel(self.after_id)
                except Exception:
                    pass
                self.after_id = None

            # Safely close serial port under lock
            with self.serial_lock:
                if self.serial_port:
                    try:
                        self.serial_port.close()
                    except Exception:
                        pass
                    self.serial_port = None

            # Join thread briefly
            if self.serial_thread and self.serial_thread.is_alive():
                self.serial_thread.join(timeout=0.2)

            self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = SerialGUI(root)
    root.mainloop()