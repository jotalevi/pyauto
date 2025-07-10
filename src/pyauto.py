import tkinter as tk
from tkinter import ttk
from pynput import mouse, keyboard
import threading
import time
import json
import os

# -------------------------
# GLOBALS
# -------------------------

events = []
recording = False
looping = False
loop_thread = None
ctrl_pressed = False

speed_multiplier = 2.0
hotkey_key = keyboard.Key.f3
hotkey_modifiers = {"ctrl": True, "alt": False, "shift": False}

mouse_controller = mouse.Controller()
progress_var = None
progress_bar = None
progress_window = None

SETTINGS_FILE = "settings.json"

# -------------------------
# SETTINGS SAVE/LOAD
# -------------------------

def load_settings():
    global speed_multiplier, hotkey_key, hotkey_modifiers

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)

            speed_multiplier = data.get("speed_multiplier", 2.0)
            hotkey_key_str = data.get("hotkey_key", "f3")
            hotkey_modifiers.update(data.get("hotkey_modifiers", {}))

            # Convert hotkey_key_str back to pynput Key object if needed
            if hotkey_key_str.lower().startswith("f") and hotkey_key_str[1:].isdigit():
                hotkey_key = getattr(keyboard.Key, hotkey_key_str.lower())
            else:
                hotkey_key = hotkey_key_str.lower()

            print("Settings loaded.")
        except Exception as e:
            print(f"Failed to load settings: {e}")
    else:
        print("No settings file found. Using defaults.")

def save_settings_to_file():
    hotkey_key_str = hotkey_key.name if isinstance(hotkey_key, keyboard.Key) else hotkey_key

    data = {
        "speed_multiplier": speed_multiplier,
        "hotkey_key": hotkey_key_str,
        "hotkey_modifiers": hotkey_modifiers
    }
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print("Settings saved to file.")
    except Exception as e:
        print(f"Failed to save settings: {e}")

def auto_save(*args):
    global speed_multiplier, hotkey_key, hotkey_modifiers

    try:
        speed_multiplier = float(speed_scale.get())
    except Exception:
        speed_multiplier = 2.0

    key_text = hotkey_entry.get().strip()
    try:
        if key_text.lower().startswith("f") and key_text[1:].isdigit():
            hotkey_key_val = getattr(keyboard.Key, key_text.lower())
        else:
            hotkey_key_val = key_text.lower()
        hotkey_key = hotkey_key_val
    except Exception:
        hotkey_key = keyboard.Key.f3

    hotkey_modifiers["ctrl"] = ctrl_var.get()
    hotkey_modifiers["alt"] = alt_var.get()
    hotkey_modifiers["shift"] = shift_var.get()

    save_settings_to_file()

# -------------------------
# MOUSE / KEYBOARD LOGIC
# -------------------------

def on_move(x, y):
    if recording:
        events.append(('move', x, y, time.time()))

def on_click(x, y, button, pressed):
    if recording:
        events.append(('click', x, y, button, pressed, time.time()))

def on_scroll(x, y, dx, dy):
    if recording:
        events.append(('scroll', x, y, dx, dy, time.time()))

def replay_events():
    global looping

    while looping:
        if not events:
            time.sleep(0.1)
            continue

        total_events = len(events)

        for i, event in enumerate(events):
            if not looping:
                break

            etype = event[0]

            if i == 0:
                delay = 0
            else:
                original_delay = event[-1] - events[i - 1][-1]
                delay = original_delay / speed_multiplier

            time.sleep(delay)

            if etype == 'move':
                _, x, y, _ = event
                mouse_controller.position = (x, y)

            elif etype == 'click':
                _, x, y, button, pressed, _ = event
                mouse_controller.position = (x, y)
                if pressed:
                    mouse_controller.press(button)
                else:
                    mouse_controller.release(button)

            elif etype == 'scroll':
                _, x, y, dx, dy, _ = event
                mouse_controller.position = (x, y)
                mouse_controller.scroll(dx, dy)

            if progress_var is not None:
                progress_var.set(int((i+1)/total_events*100))

        if progress_var is not None:
            progress_var.set(0)

def toggle_state():
    global recording, looping, events, loop_thread

    if not recording and not looping:
        print("Starting recording...")
        events.clear()
        recording = True

    elif recording and not looping:
        print("Stopping recording. Starting looping...")
        recording = False
        if not events:
            print("No events recorded.")
            return
        looping = True
        show_progress_window()
        loop_thread = threading.Thread(target=replay_events, daemon=True)
        loop_thread.start()

    elif not recording and looping:
        print("Stopping looping and clearing recorded events.")
        looping = False
        if loop_thread is not None:
            loop_thread.join()
        events.clear()
        close_progress_window()

    else:
        print("Resetting everything.")
        recording = False
        looping = False
        events.clear()

def on_press(key):
    global ctrl_pressed

    if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
        ctrl_pressed = True

    match = (
        (not hotkey_modifiers["ctrl"] or ctrl_pressed)
        and (
            (isinstance(hotkey_key, keyboard.Key) and key == hotkey_key)
            or (isinstance(hotkey_key, str) and hasattr(key, "char") and key.char == hotkey_key)
        )
    )

    if match:
        toggle_state()

def on_release(key):
    global ctrl_pressed
    if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
        ctrl_pressed = False

# -------------------------
# GUI LOGIC
# -------------------------

def show_progress_window():
    global progress_window, progress_bar, progress_var

    progress_window = tk.Toplevel(root)
    progress_window.overrideredirect(True)
    progress_window.configure(bg="#1e1e1e")

    custom_titlebar(progress_window, "Loop Progress")

    progress_var = tk.IntVar()
    progress_bar = ttk.Progressbar(progress_window, orient="horizontal", length=300, mode="determinate", maximum=100, variable=progress_var)
    progress_bar.pack(padx=20, pady=20)

def close_progress_window():
    global progress_window
    if progress_window is not None:
        progress_window.destroy()
        progress_window = None

# -------------------------
# CUSTOM WINDOW DESIGN
# -------------------------

def custom_titlebar(win, title_text):
    titlebar = tk.Frame(win, bg="#333333", relief="raised", bd=0)
    titlebar.pack(fill="x")

    title_label = tk.Label(titlebar, text=title_text, fg="white", bg="#333333", font=("Segoe UI", 10, "bold"))
    title_label.pack(side="left", padx=10)

    def start_move(event):
        win.x = event.x
        win.y = event.y

    def stop_move(event):
        win.x = None
        win.y = None

    def on_motion(event):
        dx = event.x - win.x
        dy = event.y - win.y
        x = win.winfo_x() + dx
        y = win.winfo_y() + dy
        win.geometry(f"+{x}+{y}")

    titlebar.bind("<ButtonPress-1>", start_move)
    titlebar.bind("<ButtonRelease-1>", stop_move)
    titlebar.bind("<B1-Motion>", on_motion)

    close_button = tk.Button(titlebar, text="✕", fg="white", bg="#ff4d4d", bd=0, command=win.destroy, padx=5, pady=2)
    close_button.pack(side="right", padx=5)

# -------------------------
# LAUNCH MAIN WINDOW
# -------------------------

load_settings()

root = tk.Tk()
root.overrideredirect(True)
root.configure(bg="#1e1e1e")

custom_titlebar(root, "Mouse Recorder Settings")

content = tk.Frame(root, bg="#1e1e1e")
content.pack(padx=20, pady=20)

tk.Label(content, text="Replay Speed (e.g. 2 = 2x)", fg="white", bg="#1e1e1e", font=("Segoe UI", 10)).pack(pady=(0,5))
speed_scale = tk.Scale(content, from_=0.5, to=10.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#1e1e1e", fg="white", troughcolor="#555555", highlightthickness=0, command=lambda val: auto_save())
speed_scale.pack()

tk.Label(content, text="Hotkey Key (e.g. F3, a, b)", fg="white", bg="#1e1e1e", font=("Segoe UI", 10)).pack(pady=(15, 5))
hotkey_entry = tk.Entry(content, bg="#333333", fg="white", insertbackground="white", relief="flat")
hotkey_entry.pack()

ctrl_var = tk.BooleanVar()
alt_var = tk.BooleanVar()
shift_var = tk.BooleanVar()

check_frame = tk.Frame(content, bg="#1e1e1e")
check_frame.pack(pady=10)

tk.Checkbutton(check_frame, text="Ctrl", variable=ctrl_var, bg="#1e1e1e", fg="white", activebackground="#1e1e1e", selectcolor="#333333", command=auto_save).pack(side="left", padx=5)
tk.Checkbutton(check_frame, text="Alt", variable=alt_var, bg="#1e1e1e", fg="white", activebackground="#1e1e1e", selectcolor="#333333", command=auto_save).pack(side="left", padx=5)
tk.Checkbutton(check_frame, text="Shift", variable=shift_var, bg="#1e1e1e", fg="white", activebackground="#1e1e1e", selectcolor="#333333", command=auto_save).pack(side="left", padx=5)

# Hook entry field to auto-save on typing
hotkey_entry.bind("<KeyRelease>", lambda e: auto_save())

# Populate GUI with loaded values
speed_scale.set(speed_multiplier)
hotkey_entry.delete(0, tk.END)
hotkey_entry.insert(0, hotkey_key if isinstance(hotkey_key, str) else hotkey_key.name.upper())
ctrl_var.set(hotkey_modifiers.get("ctrl", False))
alt_var.set(hotkey_modifiers.get("alt", False))
shift_var.set(hotkey_modifiers.get("shift", False))

root.geometry("400x300+500+200")

# Start listeners in background
mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
mouse_listener.start()

keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
keyboard_listener.start()

root.mainloop()
