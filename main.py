
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
import cv2
import json
import threading
import tempfile
import urllib.request
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.1.1"
VERSION_URL = "https://raw.githubusercontent.com/riad7jr/Riad-App/main/version.json"


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", BASE_DIR)
    return os.path.join(base_path, relative_path)


MUSIC_ENABLED = True
MUSIC_READY = False
MUSIC_ERROR = ""
BACKGROUND_IMAGE = None
BACKGROUND_LABEL = None
FULLSCREEN_BACKGROUND_IMAGE = None
FULLSCREEN_ENABLED = False
WINDOWED_GEOMETRY = "850x520"


def initialize_music():
    global MUSIC_READY, MUSIC_ERROR
    music_path = resource_path(os.path.join("assets", "riad_music.mp3"))
    try:
        if not os.path.isfile(music_path):
            raise FileNotFoundError(
                "Music file was not found at: " + music_path
            )

        pygame.mixer.init()
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(0.30)
        pygame.mixer.music.play(-1)
        MUSIC_READY = True
        MUSIC_ERROR = ""
    except Exception as error:
        MUSIC_READY = False
        MUSIC_ERROR = "{}: {}".format(type(error).__name__, error)


def toggle_music(button=None):
    global MUSIC_ENABLED
    if not MUSIC_READY:
        detail = MUSIC_ERROR if MUSIC_ERROR else "Unknown audio initialization error."
        messagebox.showwarning(
            "Music",
            "Music could not be started.\\n\\nDetails: " + detail
        )
        return
    MUSIC_ENABLED = not MUSIC_ENABLED
    if MUSIC_ENABLED:
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()
    if button is not None and button.winfo_exists():
        button.config(text=("MUSIC: ON" if MUSIC_ENABLED else "MUSIC: OFF"))



process = None
update_cancel_event = None

BG = "#101522"
PANEL = "#1B2538"
ACCENT = "#27A9E0"
WHITE = "#FFFFFF"
MUTED = "#AAB6C8"

root = tk.Tk()
root.title("Riad Belkacemi For AI")
root.geometry(WINDOWED_GEOMETRY)
root.resizable(False, False)
root.configure(bg=BG)


def set_home_background():
    global BACKGROUND_IMAGE, FULLSCREEN_BACKGROUND_IMAGE

    if BACKGROUND_LABEL is None:
        return

    try:
        if FULLSCREEN_ENABLED:
            image_path = resource_path(os.path.join("assets", "background_fullscreen.png"))
            if FULLSCREEN_BACKGROUND_IMAGE is None:
                FULLSCREEN_BACKGROUND_IMAGE = tk.PhotoImage(file=image_path)
            BACKGROUND_LABEL.config(image=FULLSCREEN_BACKGROUND_IMAGE)
            BACKGROUND_LABEL.image = FULLSCREEN_BACKGROUND_IMAGE
        else:
            image_path = resource_path(os.path.join("assets", "background_window.png"))
            if BACKGROUND_IMAGE is None:
                BACKGROUND_IMAGE = tk.PhotoImage(file=image_path)
            BACKGROUND_LABEL.config(image=BACKGROUND_IMAGE)
            BACKGROUND_LABEL.image = BACKGROUND_IMAGE
    except Exception:
        # Keep a plain background if either image asset is missing.
        BACKGROUND_LABEL.config(image="")
        root.configure(bg=BG)


def toggle_fullscreen(button=None):
    global FULLSCREEN_ENABLED
    FULLSCREEN_ENABLED = not FULLSCREEN_ENABLED
    root.attributes("-fullscreen", FULLSCREEN_ENABLED)

    if not FULLSCREEN_ENABLED:
        root.geometry(WINDOWED_GEOMETRY)
        root.resizable(False, False)

    set_home_background()
    if button is None:
        for widget in root.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and child.cget("text").startswith("FULLSCREEN:"):
                        button = child
                        break
    if button is not None and button.winfo_exists():
        button.config(
            text=("FULLSCREEN: ON" if FULLSCREEN_ENABLED else "FULLSCREEN: OFF")
        )


def handle_escape(event=None):
    if FULLSCREEN_ENABLED:
        toggle_fullscreen()
        return "break"


def clear_screen():
    for widget in root.winfo_children():
        widget.destroy()


def make_button(parent, text, command, color=ACCENT):
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 13, "bold"),
        bg=color,
        fg=WHITE,
        activebackground=color,
        activeforeground=WHITE,
        relief="flat",
        cursor="hand2",
        width=22,
        height=2
    )


def stop_detection():
    global process

    if process is not None:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

        process = None


def exit_app():
    stop_detection()
    root.destroy()


def check_camera():
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        camera.release()
        messagebox.showerror(
            "Camera Error",
            "No camera detected on your computer"
        )
        return False

    camera.release()
    return True


def start_detection(filename):
    global process

    if process is not None and process.poll() is None:
        messagebox.showwarning(
            "Warning",
            "A detection process is already running."
        )
        return

    if not check_camera():
        return

    try:
        if getattr(sys, "frozen", False):
            exe_files = {
                "hand.py": ("Fingers", "Fingers.exe"),
                "eyes.py": ("Eyes", "Eyes.exe"),
                "he.py": ("Both", "Both.exe")
            }

            folder_name, exe_name = exe_files[filename]
            app_root = os.path.dirname(os.path.dirname(sys.executable))
            executable = os.path.join(app_root, folder_name, exe_name)

            if not os.path.isfile(executable):
                messagebox.showerror(
                    "File Error",
                    "Cannot find " + os.path.join(folder_name, exe_name)
                )
                return

            command = [executable]

        else:
            script = os.path.join(BASE_DIR, filename)

            if not os.path.isfile(script):
                messagebox.showerror(
                    "File Error",
                    "Cannot find " + filename
                )
                return

            command = [sys.executable, script]

        process = subprocess.Popen(
            command,
            cwd=BASE_DIR
        )

        root.after(1000, check_process)

    except Exception as error:
        messagebox.showerror("Launch Error", str(error))


def check_process():
    global process

    if process is None:
        return

    if process.poll() is None:
        # Keep checking while the detection window is running.
        root.after(500, check_process)
        return

    # Detection ended (for example, after pressing ESC).
    process = None
    root.deiconify()
    root.lift()
    root.focus_force()


def home_screen():
    global BACKGROUND_LABEL
    clear_screen()
    root.configure(bg=BG)
    BACKGROUND_LABEL = tk.Label(root, bd=0, bg=BG)
    BACKGROUND_LABEL.place(x=0, y=0, relwidth=1, relheight=1)
    BACKGROUND_LABEL.lower()
    set_home_background()

    tk.Label(root, text="اللهم صلِّ وسلم على نبينا محمد ﷺ",
             font=("Segoe UI", 11, "bold"), bg=BG, fg="#69C7F2").pack(pady=(8, 0))
    tk.Label(root, text="Riad Belkacemi for Ai", font=("Segoe UI", 30, "bold"),
             bg="#10233A", fg=WHITE).pack(pady=(105, 20))
    make_button(root, "CONTINUE", mode_screen).pack(pady=(45, 12))
    make_button(root, "EXIT", exit_app, "#A83245").pack()

    controls_frame = tk.Frame(root, bg="#10233A")
    controls_frame.place(relx=0.5, rely=0.88, anchor="center")
    music_button = tk.Button(controls_frame, text=("MUSIC: ON" if MUSIC_ENABLED else "MUSIC: OFF"),
        command=lambda: toggle_music(music_button), font=("Segoe UI", 9, "bold"),
        bg="#10233A", fg=WHITE, activebackground="#1B3B5C", relief="flat", cursor="hand2", padx=12, pady=5)
    music_button.pack(side="left", padx=6)
    fullscreen_button = tk.Button(controls_frame,
        text=("FULLSCREEN: ON" if FULLSCREEN_ENABLED else "FULLSCREEN: OFF"),
        command=lambda: toggle_fullscreen(fullscreen_button), font=("Segoe UI", 9, "bold"),
        bg="#10233A", fg=WHITE, activebackground="#1B3B5C", relief="flat", cursor="hand2", padx=12, pady=5)
    fullscreen_button.pack(side="left", padx=6)
    tk.Label(root, text="Version " + VERSION, font=("Segoe UI", 9), bg=BG, fg=MUTED).place(relx=0.015, rely=0.985, anchor="sw")
    tk.Button(root, text="Check for update", command=update_message, bg=BG, fg=ACCENT,
              activebackground=BG, relief="flat", cursor="hand2").place(relx=0.985, rely=0.985, anchor="se")


def _draw_mode_card(parent, title, subtitle, command, border_color, title_color):
    # Rounded, thin colored outline with a very light blue-tinted interior.
    card = tk.Canvas(parent, height=74, bg=BG, highlightthickness=0,
                     bd=0, cursor="hand2")
    card.pack(fill="x", padx=6, pady=6)

    def draw(event=None):
        card.delete("all")
        width = max(card.winfo_width(), 300)
        height = 74
        radius = 13
        points = [
            radius, 1, width-radius, 1,
            width-1, 1, width-1, radius,
            width-1, height-radius, width-1, height-1,
            width-radius, height-1, radius, height-1,
            1, height-1, 1, height-radius,
            1, radius, 1, 1, radius, 1
        ]
        card.create_polygon(points, smooth=True, splinesteps=24,
                            fill="#F2F6FC", outline=border_color, width=1.2)
        card.create_text(width / 2, 27, text=title,
                         font=("Segoe UI", 16, "bold"), fill=title_color)
        card.create_text(width / 2, 54, text=subtitle,
                         font=("Segoe UI", 9), fill="#777777")

    card.bind("<Configure>", draw)
    card.bind("<Button-1>", lambda event: command())
    return card


def mode_screen():
    clear_screen()
    root.configure(bg=BG)
    tk.Label(root, text="CHOOSE YOUR MODE", font=("Segoe UI", 25, "bold"), bg=BG, fg=WHITE).pack(pady=(75, 38))
    _draw_mode_card(root, "DETECTION", "Driver Monitoring System",
                    detection_screen, "#35AE61", "#00692A")
    _draw_mode_card(root, "MATH WITH RIAD", "Mathematical & Engineering Tools",
                    math_home_screen, "#3B82F6", "#3B82F6")
    make_button(root, "HOME", home_screen, "#46536A").pack(pady=24)


def detection_screen():
    clear_screen()
    root.configure(bg=BG)
    tk.Label(root, text="SELECT DETECTION MODE", font=("Segoe UI", 24, "bold"), bg=BG, fg=WHITE).pack(pady=(55, 28))
    make_button(root, "FINGERS", lambda: start_detection("hand.py")).pack(pady=9)
    make_button(root, "EYES", lambda: start_detection("eyes.py")).pack(pady=9)
    make_button(root, "BOTH (F & E)", lambda: start_detection("he.py")).pack(pady=9)
    make_button(root, "BACK", mode_screen, "#46536A").pack(pady=22)


def math_home_screen():
    clear_screen()
    root.configure(bg=BG)
    tk.Label(root, text="MATH WITH RIAD", font=("Segoe UI", 25, "bold"), bg=BG, fg=WHITE).pack(pady=(55, 12))
    tk.Label(root, text="Mathematical & Engineering Tools", font=("Segoe UI", 11), bg=BG, fg=MUTED).pack(pady=(0, 30))
    tk.Button(root, text="COMPLEX NUMBER CONVERTER", command=complex_converter_screen,
        font=("Segoe UI", 13, "bold"), bg="#2563A6", fg=WHITE, relief="flat", cursor="hand2", width=30, height=2).pack(pady=12)
    make_button(root, "BACK", mode_screen, "#46536A").pack(pady=25)


def parse_angle(value):
    import math
    text = value.strip().lower().replace("π", "p").replace(" ", "")
    if not text:
        raise ValueError("Please enter an angle.")
    # Accept numeric expressions containing p, +, -, *, / and parentheses only.
    import ast
    import re
    expression = text.replace("p", "pi")
    expression = re.sub(r"(\d)(pi)", r"\1*\2", expression)
    tree = ast.parse(expression, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div,
               ast.Pow, ast.USub, ast.UAdd, ast.Constant, ast.Name, ast.Load, ast.Call)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError("Use numbers, p (π), sqrt(), and ** for powers.")
        if isinstance(node, ast.Name) and node.id not in ("pi", "sqrt"):
            raise ValueError("Use p for π and sqrt() for square roots.")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id != "sqrt" or len(node.args) != 1 or node.keywords):
            raise ValueError("Only sqrt(number) is supported.")
    return float(eval(compile(tree, "<angle>", "eval"), {"__builtins__": {}}, {"pi": math.pi, "sqrt": math.sqrt}))


def parse_real_number(value):
    """Safely evaluate a real-number expression such as sqrt(2), 2**3 or 3/4."""
    import ast
    import math
    import re
    expression = value.strip().lower().replace("π", "pi").replace("^", "**")
    # Accept leading-zero integer literals as decimal numbers (01 -> 1).
    expression = re.sub(r"(?<![A-Za-z0-9_.])0+([0-9]+)(?![A-Za-z0-9_.])", r"\1", expression)
    if not expression:
        raise ValueError("Please enter a number.")
    tree = ast.parse(expression, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div,
               ast.Pow, ast.USub, ast.UAdd, ast.Constant, ast.Name, ast.Load, ast.Call)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError("Use numbers, +, -, *, /, **, sqrt(), and pi.")
        if isinstance(node, ast.Name) and node.id not in ("pi", "sqrt"):
            raise ValueError("Use sqrt() for roots and pi for π.")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id != "sqrt" or len(node.args) != 1 or node.keywords):
            raise ValueError("Only sqrt(number) is supported.")
    result = float(eval(compile(tree, "<number>", "eval"), {"__builtins__": {}}, {"pi": math.pi, "sqrt": math.sqrt}))
    if not math.isfinite(result):
        raise ValueError("The result must be a finite real number.")
    return result


def parse_numeric_expression(value):
    """Safely evaluate numeric expressions such as sqrt(2), 2^3 and p/2."""
    import ast
    import math
    import re
    text = value.strip().lower().replace("π", "p").replace(" ", "")
    if not text:
        raise ValueError("Please enter a number or mathematical expression.")
    text = text.replace("^", "**").replace("p", "pi")
    text = re.sub(r"(\d)(pi)", r"\1*\2", text)
    # Accept leading-zero integer literals as decimal numbers (01 -> 1).
    text = re.sub(r"(?<![A-Za-z0-9_.])0+([0-9]+)(?![A-Za-z0-9_.])", r"\1", text)
    tree = ast.parse(text, mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.Pow, ast.USub, ast.UAdd, ast.Constant, ast.Name,
               ast.Load, ast.Call)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError("Use numbers, +, -, *, /, ^, sqrt() and p (π).")
        if isinstance(node, ast.Name) and node.id not in ("pi", "sqrt"):
            raise ValueError("Only sqrt() and p (π) are supported functions/constants.")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id != "sqrt" or len(node.args) != 1 or node.keywords):
            raise ValueError("Use sqrt(number), for example sqrt(2).")
    result = eval(compile(tree, "<numeric>", "eval"), {"__builtins__": {}}, {"pi": math.pi, "sqrt": math.sqrt})
    return float(result)


def complex_converter_screen():
    PAGE_BG = "#ECEFF1"       # light gray, replacing the dark blue converter background
    TEXT = "#252A32"
    MUTED_TEXT = "#68727D"
    GREEN = "#15934D"
    BLUE = "#347FE5"
    PURPLE = "#A34DE8"

    clear_screen()
    root.configure(bg=PAGE_BG)

    # Fixed top area: title and input controls.
    top = tk.Frame(root, bg=PAGE_BG)
    top.pack(fill="x", padx=22, pady=(12, 4))
    tk.Label(top, text="COMPLEX NUMBER CONVERTER",
             font=("Segoe UI", 20, "bold"), bg=PAGE_BG, fg=TEXT).pack(pady=(2, 8))

    form = tk.StringVar(value="Algebraic")
    unit = tk.StringVar(value="Radian")
    result_mode = tk.StringVar(value="Both")  # Results are always shown in exact + decimal form.

    # Input form selector: three clear, color-coded mathematical cards.
    form_panel = tk.Frame(top, bg="#FFFFFF", highlightbackground="#E1E5EA",
                          highlightthickness=1, padx=8, pady=7)
    form_panel.pack(fill="x", pady=(0, 7))
    tk.Label(form_panel, text="Choose Input Form", bg="#FFFFFF", fg=TEXT,
             font=("Segoe UI", 10, "bold")).pack(anchor="e", padx=5, pady=(0, 5))
    selector = tk.Frame(form_panel, bg="#FFFFFF")
    selector.pack(fill="x")
    form_buttons = {}
    form_styles = {
        "Exponential": ("#F4ECFC", PURPLE, "reʲᶿ"),
        "Trigonometric": ("#E6F5F0", "#15966A", "r(cosθ + jsinθ)"),
        "Algebraic": ("#EAF1FC", BLUE, "a + bj")
    }
    def choose_form(name):
        form.set(name)
        for key, button in form_buttons.items():
            bg_color, fg_color, _symbol = form_styles[key]
            button.configure(bg=bg_color, fg=fg_color,
                             relief=("solid" if key == name else "flat"),
                             bd=(1 if key == name else 0),
                             highlightthickness=(1 if key == name else 0),
                             highlightbackground=fg_color)
        refresh_fields()
    for name in ("Exponential", "Trigonometric", "Algebraic"):
        bg_color, fg_color, symbol = form_styles[name]
        button = tk.Button(selector, text=name + "\n" + symbol,
                           command=lambda n=name: choose_form(n),
                           font=("Segoe UI", 10, "bold"), bg=bg_color, fg=TEXT,
                           activebackground=bg_color, activeforeground=TEXT,
                           relief="flat", bd=0, cursor="hand2", height=2)
        button.pack(side="left", fill="x", expand=True, padx=3)
        form_buttons[name] = button
    form_buttons["Algebraic"].configure(relief="solid", bd=1, highlightthickness=1,
                                        highlightbackground=BLUE)

    fields = tk.Frame(top, bg=PAGE_BG)
    fields.pack(fill="x", pady=2)

    # Scrollable results area. The BACK button stays fixed below it.
    results_shell = tk.Frame(root, bg=PAGE_BG)
    results_shell.pack(fill="both", expand=True, padx=22, pady=(4, 2))
    canvas = tk.Canvas(results_shell, bg=PAGE_BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(results_shell, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    result_frame = tk.Frame(canvas, bg=PAGE_BG)
    result_window = canvas.create_window((0, 0), window=result_frame, anchor="nw")

    def update_scroll_region(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(result_window, width=canvas.winfo_width())

    result_frame.bind("<Configure>", update_scroll_region)
    canvas.bind("<Configure>", update_scroll_region)

    def mousewheel(event):
        if getattr(event, "delta", 0):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif getattr(event, "num", None) == 4:
            canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            canvas.yview_scroll(1, "units")

    canvas.bind_all("<MouseWheel>", mousewheel)
    canvas.bind_all("<Button-4>", mousewheel)
    canvas.bind_all("<Button-5>", mousewheel)

    def refresh_fields():
        for widget in fields.winfo_children():
            widget.destroy()
        inputs["entries"] = ()
        if form.get() == "Algebraic":
            field_color = GREEN
            tk.Label(fields, text="Real part (a)", bg=PAGE_BG, fg=field_color,
                     font=("Segoe UI", 12)).pack()
            real_entry = tk.Entry(fields, font=("Segoe UI", 12), justify="center", width=28, relief="solid", bd=1)
            real_entry.pack(pady=2, ipady=2)
            tk.Label(fields, text="Imaginary part (b) — enter number only, no j",
                     bg=PAGE_BG, fg=field_color, font=("Segoe UI", 12)).pack()
            imag_entry = tk.Entry(fields, font=("Segoe UI", 12), justify="center", width=28, relief="solid", bd=1)
            imag_entry.pack(pady=2, ipady=2)
            real_entry.focus_set()
            real_entry.bind("<Return>", lambda event: imag_entry.focus_set())
            imag_entry.bind("<Return>", lambda event: convert())
            inputs["entries"] = (real_entry, imag_entry)

        else:
            options_panel = tk.Frame(fields, bg="#FFFFFF", highlightbackground="#E1E5EA",
                                     highlightthickness=1, padx=9, pady=6)
            options_panel.pack(fill="x", pady=(2, 5))
            tk.Label(options_panel, text="Step 1 — Select Angle Unit", bg="#FFFFFF",
                     fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="e", pady=(0, 4))
            unit_row = tk.Frame(options_panel, bg="#FFFFFF")
            unit_row.pack(fill="x")
            unit_buttons = {}
            def choose_unit(value):
                unit.set(value)
                for key, button in unit_buttons.items():
                    button.configure(relief=("solid" if key == value else "flat"),
                                     bd=(1 if key == value else 0),
                                     highlightthickness=(1 if key == value else 0),
                                     highlightbackground=BLUE)
            for label, caption in (("Radian", "RADIAN (π)"), ("Degree", "(°) DEGREE")):
                button = tk.Button(unit_row, text=caption, command=lambda v=label: choose_unit(v),
                                   bg="#EAF1FC", fg=TEXT, activebackground="#EAF1FC",
                                   relief="flat", bd=0, font=("Segoe UI", 9, "bold"),
                                   cursor="hand2", pady=7)
                button.pack(side="left", fill="x", expand=True, padx=3)
                unit_buttons[label] = button
            choose_unit(unit.get())
            tk.Label(fields, text="Module (r)", bg=PAGE_BG, fg=BLUE,
                     font=("Segoe UI", 12)).pack(pady=(2, 0))
            mag_entry = tk.Entry(fields, font=("Segoe UI", 12), justify="center", width=28, relief="solid", bd=1)
            mag_entry.pack(pady=2, ipady=2)
            tk.Label(fields, text="Angle (θ) — use p for π in Radian mode",
                     bg=PAGE_BG, fg=BLUE, font=("Segoe UI", 12)).pack()
            angle_entry = tk.Entry(fields, font=("Segoe UI", 12), justify="center", width=28, relief="solid", bd=1)
            angle_entry.pack(pady=2, ipady=2)
            mag_entry.focus_set()
            mag_entry.bind("<Return>", lambda event: angle_entry.focus_set())
            angle_entry.bind("<Return>", lambda event: convert())
            inputs["entries"] = (mag_entry, angle_entry)

        # Subtle left-side syntax guide for mathematical input.
        hint = "π : p\npower : **\nsqrt(x) : √x"
        hint_label = tk.Label(fields, text=hint, justify="left", anchor="w",
                              bg=PAGE_BG, fg="#858B92",
                              font=("Segoe UI", 12))
        hint_label.place(relx=0.015, rely=0.48, anchor="w")

        tk.Button(fields, text="CONVERT", command=convert, bg="#1689D4", fg="#FFFFFF",
                  font=("Segoe UI", 10, "bold"), relief="flat", padx=24, pady=5,
                  cursor="hand2").pack(pady=5)

    def show_results(z, theta_rad, magnitude, exact_angle=None):
        import math
        for widget in result_frame.winfo_children():
            widget.destroy()

        PAGE = "#ECEFF1"
        TEXT_COLOR = "#252A32"
        LINE = "#D5DADF"
        CARD_BG = "#FFFFFF"
        BLUE_BG = CARD_BG
        PURPLE_BG = CARD_BG
        GREEN_BG = CARD_BG
        result_frame.configure(bg=PAGE)

        theta_deg = math.degrees(theta_rad)
        a, b = z.real, z.imag

        def num(value):
            if abs(value) < 1e-10:
                value = 0.0
            return "{:.6g}".format(value)

        def exact_pi_text(rad_value):
            # Recognize common exact angles, including angles obtained from
            # algebraic inputs (for example 1+j -> pi/4), not only typed p-values.
            from fractions import Fraction
            import math
            ratio = rad_value / math.pi
            fraction = Fraction(ratio).limit_denominator(48)
            if abs(float(fraction) - ratio) > 1e-8:
                return None
            numerator, denominator = fraction.numerator, fraction.denominator
            if numerator == 0:
                return "0"
            sign = "−" if numerator < 0 else ""
            numerator = abs(numerator)
            if denominator == 1:
                core = "π" if numerator == 1 else "{}π".format(numerator)
            else:
                top = "π" if numerator == 1 else "{}π".format(numerator)
                core = "{}/{}".format(top, denominator)
            return sign + core

        def angle_text(rad_value):
            return exact_pi_text(rad_value) or num(rad_value)

        algebraic = "Z = {} {} j{}".format(num(a), "+" if b >= 0 else "−", num(abs(b)))
        rad_label = angle_text(theta_rad)
        deg_label = num(theta_deg) + "°"
        r_text = num(magnitude)
        trig_rad = "Z = {} ( cos {} + j sin {} )".format(r_text, rad_label, rad_label)
        trig_deg = "Z = {} ( cos {} + j sin {} )".format(r_text, deg_label, deg_label)
        def superscript(value):
            # Unicode mathematical superscripts keep the exponent visually raised.
            table = str.maketrans({
                "j": "ʲ", "0": "⁰", "1": "¹", "2": "²", "3": "³",
                "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸",
                "9": "⁹", ".": "·", "-": "⁻", "−": "⁻", "+": "⁺",
                "/": "⁄", "(": "⁽", ")": "⁾"
            })
            value = str(value).replace("π", "π")
            # Put π between raised digits where applicable (e.g. 3π/4 -> ³π⁄⁴).
            return value.translate(table)

        exp_rad = "Z = {}e{}".format(r_text, superscript("j" + rad_label))
        exp_deg = "Z = {}e{}".format(r_text, superscript("j" + deg_label))

        header = tk.Frame(result_frame, bg=PAGE)
        header.pack(fill="x", padx=10, pady=(8, 12))
        tk.Label(header, text="Conversion Results", bg=PAGE, fg="#4A4F56",
                 font=("Segoe UI", 19, "bold")).pack(anchor="e")

        def separator():
            tk.Frame(result_frame, bg=LINE, height=1).pack(fill="x", padx=8, pady=8)

        def section_title(title):
            tk.Label(result_frame, text=title, bg=PAGE, fg=TEXT_COLOR,
                     font=("Segoe UI", 11, "bold")).pack(anchor="e", padx=12, pady=(3, 5))

        def formula_card(label, value, color, card_bg, exponent=None, border_color="#DCE3EA"):
            card = tk.Frame(result_frame, bg=card_bg, height=96,
                            bd=0, highlightthickness=1,
                            highlightbackground=border_color,
                            highlightcolor=border_color)
            card.pack(fill="x", padx=8, pady=3)
            card.pack_propagate(False)
            tk.Label(card, text=label, bg=card_bg, fg=color,
                     font=("Segoe UI", 10, "bold")).pack(anchor="e", padx=12, pady=(9, 0))
            if exponent is None:
                tk.Label(card, text=value, bg=card_bg, fg="#20242A",
                         font=("Cambria Math", 22), justify="center",
                         wraplength=900).pack(fill="both", expand=True, padx=12, pady=(0, 7))
            else:
                # Render e^(j theta) as two aligned pieces so the complete
                # exponent (including pi, decimal point and degree sign) is
                # visibly raised, like conventional mathematical typesetting.
                equation = tk.Frame(card, bg=card_bg)
                equation.pack(expand=True, pady=(5, 12))
                tk.Label(equation, text=value, bg=card_bg, fg="#20242A",
                         font=("Cambria Math", 22), padx=0, borderwidth=0).pack(side="left", anchor="s", padx=(0, 0))
                tk.Label(equation, text=exponent, bg=card_bg, fg="#20242A",
                         font=("Cambria Math", 15), padx=0, borderwidth=0).pack(side="left", anchor="n", pady=(0, 13), padx=(0, 0))

        # Algebraic output uses the same framed card layout as the other forms.
        formula_card("ALGEBRAIC FORM", algebraic, "#15934D", CARD_BG,
                     border_color="#CDEBD9")
        separator()

        section_title("Trigonometric Form")
        formula_card("RADIANS", trig_rad, BLUE, BLUE_BG,
                     border_color="#D2E3FA")
        formula_card("DEGREES", trig_deg, BLUE, BLUE_BG,
                     border_color="#D2E3FA")
        separator()

        section_title("Exponential Form")
        formula_card("RADIANS", "Z = {} e".format(r_text), PURPLE, PURPLE_BG,
                     exponent="j " + rad_label, border_color="#D2E3FA")
        formula_card("DEGREES", "Z = {} e".format(r_text), PURPLE, PURPLE_BG,
                     exponent="j " + deg_label, border_color="#D2E3FA")
        canvas.yview_moveto(0)
        result_frame.update_idletasks()
        update_scroll_region()

    inputs = {}

    def convert():
        import math
        try:
            first, second = inputs["entries"]
            if form.get() == "Algebraic":
                a = parse_real_number(first.get())
                b = parse_real_number(second.get())
                z = complex(a, b)
                magnitude = abs(z)
                theta = math.atan2(b, a)
                exact = None
            else:
                magnitude = parse_numeric_expression(first.get())
                if magnitude < 0:
                    raise ValueError("Module must be zero or positive.")
                entered = second.get().strip()
                angle = parse_angle(entered)
                theta = angle if unit.get() == "Radian" else math.radians(angle)
                z = complex(magnitude * math.cos(theta), magnitude * math.sin(theta))
                exact = entered if unit.get() == "Radian" else None
            show_results(z, theta, magnitude, exact)
        except Exception as error:
            messagebox.showerror("Invalid input", str(error))

    refresh_fields()
    bottom = tk.Frame(root, bg=PAGE_BG)
    bottom.pack(fill="x", side="bottom", pady=(2, 8))
    tk.Button(bottom, text="BACK", command=math_home_screen,
              font=("Segoe UI", 10, "bold"), bg="#68727D", fg="#FFFFFF",
              activebackground="#56616C", activeforeground="#FFFFFF",
              relief="flat", cursor="hand2", padx=34, pady=7).pack()

def version_tuple(version):
    try:
        return tuple(int(part) for part in version.strip().lstrip("vV").split("."))
    except (ValueError, AttributeError):
        return (0,)


def is_newer_version(latest, current):
    latest_parts = version_tuple(latest)
    current_parts = version_tuple(current)
    length = max(len(latest_parts), len(current_parts))
    latest_parts += (0,) * (length - len(latest_parts))
    current_parts += (0,) * (length - len(current_parts))
    return latest_parts > current_parts



def update_panel(title, subtitle, button_text=None, button_command=None,
                 show_progress=False, cancel_command=None):
    clear_screen()
    root.configure(bg="#F2F5F9")

    tk.Label(
        root, text="اللهم صلِّ وسلم على نبينا محمد ﷺ",
        font=("Segoe UI", 13, "bold"), bg="#F2F5F9", fg="#176FA6"
    ).pack(pady=(18, 5))

    card = tk.Frame(
        root, bg="#FFFFFF", padx=34, pady=24,
        highlightthickness=1, highlightbackground="#DCE5EF"
    )
    card.place(relx=0.5, rely=0.54, anchor="center", width=710, height=340)

    header = tk.Frame(card, bg="#FFFFFF")
    header.pack(fill="x")
    tk.Label(
        header, text="↻", font=("Segoe UI Symbol", 48, "bold"),
        bg="#FFFFFF", fg="#1689D4", width=2
    ).pack(side="left", padx=(0, 18))

    text_area = tk.Frame(header, bg="#FFFFFF")
    text_area.pack(side="left", fill="x", expand=True)
    tk.Label(
        text_area, text="RIAD APP  •  SOFTWARE UPDATE",
        font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#1689D4"
    ).pack(anchor="w")
    tk.Label(
        text_area, text=title, font=("Segoe UI", 22, "bold"),
        bg="#FFFFFF", fg="#172437"
    ).pack(anchor="w", pady=(5, 4))
    tk.Label(
        text_area, text=subtitle, font=("Segoe UI", 10),
        bg="#FFFFFF", fg="#64748B", wraplength=500, justify="left"
    ).pack(anchor="w")

    tk.Frame(card, bg="#E8EEF5", height=1).pack(fill="x", pady=(20, 16))

    progress_frame = tk.Frame(card, bg="#FFFFFF")
    progress_frame.pack(fill="x")
    progress_text = tk.Label(
        progress_frame, text="0%", font=("Segoe UI", 10, "bold"),
        bg="#FFFFFF", fg="#334155"
    )
    progress_text.pack(anchor="e", pady=(0, 7))
    canvas = tk.Canvas(
        progress_frame, height=12, bg="#E7EDF4", highlightthickness=0, bd=0
    )
    canvas.pack(fill="x")
    if not show_progress:
        progress_frame.pack_forget()

    buttons = tk.Frame(card, bg="#FFFFFF")
    buttons.pack(fill="x", pady=(20, 0))
    if cancel_command:
        tk.Button(
            buttons, text="CANCEL", command=cancel_command,
            font=("Segoe UI", 10, "bold"), bg="#EEF2F7", fg="#475569",
            activebackground="#E2E8F0", activeforeground="#1E293B",
            relief="flat", cursor="hand2", padx=22, pady=10
        ).pack(side="left")
    if button_text and button_command:
        tk.Button(
            buttons, text=button_text, command=button_command,
            font=("Segoe UI", 11, "bold"), bg="#1689D4", fg="#FFFFFF",
            activebackground="#0876BE", activeforeground="#FFFFFF",
            relief="flat", cursor="hand2", padx=25, pady=10
        ).pack(side="right")

    return {"canvas": canvas, "percent": progress_text}


def set_update_progress(ui, percent):
    if not root.winfo_exists():
        return
    percent = max(0, min(100, int(percent)))
    canvas = ui["canvas"]
    canvas.delete("all")
    width = max(1, canvas.winfo_width())
    fill_width = int(width * percent / 100.0)
    if fill_width:
        canvas.create_rectangle(
            0, 0, fill_width, 12, fill="#1689D4", outline="#1689D4"
        )
    ui["percent"].config(text="{}%".format(percent))


def cancel_update_download():
    global update_cancel_event
    if update_cancel_event is not None:
        update_cancel_event.set()


def update_available_screen(latest, download_url):
    update_panel(
        "Updates available",
        "Version {} is ready to download. Your current version is {}."
        .format(latest, VERSION),
        button_text="DOWNLOAD",
        button_command=lambda: download_and_launch_update(download_url, latest),
        cancel_command=home_screen
    )

def update_message():
    button = None
    for widget in root.winfo_children():
        if isinstance(widget, tk.Button) and widget.cget("text") == "Check for update":
            button = widget
            break
    if button is not None:
        button.config(state="disabled", text="Checking...")

    result = {"error": False, "version": "", "download_url": ""}

    def show_result():
        if button is not None and button.winfo_exists():
            button.config(state="normal", text="Check for update")
        if result["error"]:
            messagebox.showwarning(
                "Updates",
                "Unable to check for updates. Please check your internet connection.\n"
                "Riad App will continue working normally."
            )
            return
        latest = result["version"]
        download_url = result["download_url"]
        if not is_newer_version(latest, VERSION):
            messagebox.showinfo("Updates", "You are using the latest version.")
            return
        if not download_url.startswith(
            "https://github.com/riad7jr/Riad-App/releases/download/"
        ):
            messagebox.showerror("Updates", "The update download link is invalid.")
            return
        update_available_screen(latest, download_url)

    def check_worker():
        try:
            request = urllib.request.Request(
                VERSION_URL, headers={"User-Agent": "Riad-App-Updater"}
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            result["version"] = str(data.get("version", "")).strip()
            result["download_url"] = str(data.get("download_url", "")).strip()
            if not result["version"] or not result["download_url"]:
                raise ValueError("Incomplete version.json")
        except Exception:
            result["error"] = True
        root.after(0, show_result)

    threading.Thread(target=check_worker, daemon=True).start()


def download_and_launch_update(download_url, latest_version):
    global update_cancel_event
    update_cancel_event = threading.Event()
    cancel_event = update_cancel_event

    safe_version = latest_version.replace(".", "_")
    installer_path = os.path.join(
        tempfile.gettempdir(), "Riad_App_Setup_" + safe_version + ".exe"
    )
    ui = update_panel(
        "Downloading update",
        "Downloading Riad App {}. You can cancel safely at any time."
        .format(latest_version),
        show_progress=True,
        cancel_command=cancel_update_download
    )

    def download_worker():
        try:
            if os.path.exists(installer_path):
                os.remove(installer_path)

            request = urllib.request.Request(
                download_url, headers={"User-Agent": "Riad-App-Updater"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                header = response.headers.get("Content-Length")
                total_size = int(header) if header else 0
                downloaded = 0
                with open(installer_path, "wb") as installer_file:
                    while True:
                        if cancel_event.is_set():
                            raise InterruptedError("Download cancelled")
                        chunk = response.read(256 * 1024)
                        if not chunk:
                            break
                        if cancel_event.is_set():
                            raise InterruptedError("Download cancelled")
                        installer_file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            root.after(
                                0, lambda p=percent: set_update_progress(ui, p)
                            )

            if cancel_event.is_set():
                raise InterruptedError("Download cancelled")
            if not os.path.isfile(installer_path) or os.path.getsize(installer_path) == 0:
                raise IOError("Downloaded installer is empty")
            if total_size > 0 and downloaded != total_size:
                raise IOError("Downloaded file is incomplete")

            def show_install_ready():
                update_panel(
                    "Download complete",
                    "Riad App {} is ready. Click INSTALL to open the setup wizard."
                    .format(latest_version),
                    button_text="INSTALL",
                    button_command=lambda: install_downloaded_update(
                        installer_path, latest_version
                    ),
                    cancel_command=home_screen
                )
            root.after(0, show_install_ready)

        except InterruptedError:
            try:
                if os.path.exists(installer_path):
                    os.remove(installer_path)
            except OSError:
                pass

            def show_cancelled():
                update_panel(
                    "Download cancelled",
                    "The incomplete file was deleted. Your current app is unchanged.",
                    button_text="BACK TO HOME",
                    button_command=home_screen
                )
            root.after(0, show_cancelled)

        except Exception:
            try:
                if os.path.exists(installer_path):
                    os.remove(installer_path)
            except OSError:
                pass

            def show_download_error():
                messagebox.showerror(
                    "Download Error",
                    "Unable to download the update. The incomplete file was deleted."
                )
                home_screen()
            root.after(0, show_download_error)

    threading.Thread(target=download_worker, daemon=True).start()

def install_downloaded_update(installer_path, latest_version):
    update_panel(
        "Installing new update",
        "Starting the installer for version {}. Riad App will close "
        "while the update is installed.".format(latest_version)
    )
    root.update_idletasks()

    def launch_installer():
        try:
            # Inno Setup's own progress window is shown. The app cannot
            # truthfully display the install percentage from its process.
            subprocess.Popen(
                [installer_path],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            root.after(700, exit_app)
        except Exception as error:
            messagebox.showerror("Update Error", str(error))
            home_screen()

    root.after(350, launch_installer)



# ---------------------------------------------------------------------------
# PIN protection screen
# ---------------------------------------------------------------------------
APP_PIN = "071225"
PIN_ATTEMPTS = 0
PIN_REENTRY_LIMIT = 3


def pin_state_path():
    """Store PIN progress outside the installation folder."""
    app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    state_dir = os.path.join(app_data, "RiadApp")
    return os.path.join(state_dir, "pin_state.json")


def save_pin_state(reentries=0, unlocked=False):
    try:
        state_path = pin_state_path()
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as state_file:
            json.dump({"unlocked": unlocked, "reentries": reentries}, state_file)
        return True
    except Exception:
        return False


def should_skip_pin():
    """Skip PIN permanently after three launches following first verification."""
    try:
        with open(pin_state_path(), "r", encoding="utf-8") as state_file:
            state = json.load(state_file)
        if not state.get("unlocked", False):
            return False

        reentries = int(state.get("reentries", 0)) + 1
        save_pin_state(reentries=reentries, unlocked=True)
        return reentries >= PIN_REENTRY_LIMIT
    except Exception:
        return False


def pin_screen():
    """Require the fixed PIN before allowing access to the application."""
    clear_screen()
    root.configure(bg=BG)

    tk.Label(root, text="Riad Belkacemi for Ai",
             font=("Segoe UI", 25, "bold"), bg=BG, fg=WHITE).pack(pady=(78, 8))
    tk.Label(root, text="SECURE ACCESS",
             font=("Segoe UI", 11, "bold"), bg=BG, fg="#69C7F2").pack(pady=(0, 18))

    # Hint button stays in the upper-right corner.
    hint_button = tk.Button(
        root, text="Hint", command=None,
        font=("Segoe UI", 9, "bold"), bg=PANEL, fg=WHITE,
        activebackground="#26364F", activeforeground=WHITE,
        relief="flat", cursor="hand2", padx=12, pady=5
    )
    hint_button.place(relx=0.975, rely=0.035, anchor="ne")

    hint_message = tk.Label(
        root, text="", font=("Segoe UI", 10, "bold"),
        bg=BG, fg="#69C7F2"
    )
    hint_message.place(relx=0.975, rely=0.105, anchor="ne")

    hint_after_id = [None]

    def show_hint():
        if hint_after_id[0] is not None:
            root.after_cancel(hint_after_id[0])
        hint_message.config(text="Ask Belkacemi")
        hint_after_id[0] = root.after(
            3000, lambda: hint_message.config(text="") if hint_message.winfo_exists() else None
        )

    hint_button.config(command=show_hint)

    card = tk.Frame(root, bg=PANEL, padx=38, pady=28,
                    highlightthickness=1, highlightbackground="#2C3D56")
    card.place(relx=0.5, rely=0.56, anchor="center", width=440, height=250)

    tk.Label(card, text="ENTER YOUR PIN",
             font=("Segoe UI", 15, "bold"), bg=PANEL, fg=WHITE).pack(pady=(5, 20))

    pin_frame = tk.Frame(card, bg="#FFFFFF", width=340, height=48,
                         highlightthickness=2, highlightbackground=ACCENT)
    pin_frame.place(relx=0.5, y=80, anchor="n")
    pin_frame.pack_propagate(False)

    pin_entry = tk.Entry(
        pin_frame, show="•", font=("Segoe UI", 16),
        justify="center", relief="flat", bd=0,
        bg="#FFFFFF", fg="#172437", insertbackground="#172437"
    )
    pin_entry.pack(side="left", fill="both", expand=True, padx=(12, 4), pady=5)

    visible = [False]
    show_button = tk.Button(
        pin_frame, text="SHOW", font=("Segoe UI", 8, "bold"),
        bg="#FFFFFF", fg="#526174", activebackground="#FFFFFF",
        relief="flat", cursor="hand2", padx=8
    )
    show_button.pack(side="right", padx=(0, 8))

    def toggle_pin_visibility():
        visible[0] = not visible[0]
        pin_entry.config(show="" if visible[0] else "•")
        show_button.config(text="HIDE" if visible[0] else "SHOW")

    show_button.config(command=toggle_pin_visibility)

    status_label = tk.Label(card, text="", font=("Segoe UI", 9),
                            bg=PANEL, fg="#F28B82")
    status_label.place(relx=0.5, y=132, anchor="n")

    def shake_pin_frame():
        # Only the PIN input frame moves; the buttons and the rest of the
        # window remain stationary.
        offsets = [0, -4, 4, -3, 3, -1, 1, 0]

        def move(index=0):
            if not pin_frame.winfo_exists():
                return
            if index < len(offsets):
                pin_frame.place_configure(x=offsets[index])
                root.after(22, lambda: move(index + 1))
            else:
                pin_frame.place_configure(x=0)
        move()

    def confirm_pin():
        global PIN_ATTEMPTS
        entered_pin = pin_entry.get()

        if entered_pin == APP_PIN:
            PIN_ATTEMPTS = 0
            # Mark the PIN as verified only on the first successful entry.
            # Do not reset the launch counter when the PIN is entered again;
            # otherwise every protected launch would restart the count at zero.
            try:
                with open(pin_state_path(), "r", encoding="utf-8") as state_file:
                    previous_state = json.load(state_file)
                if previous_state.get("unlocked", False):
                    current_reentries = int(previous_state.get("reentries", 0))
                else:
                    current_reentries = 0
            except Exception:
                current_reentries = 0
            save_pin_state(reentries=current_reentries, unlocked=True)
            # Start background music only after successful PIN verification.
            initialize_music()
            home_screen()
            return

        PIN_ATTEMPTS += 1
        pin_entry.delete(0, tk.END)
        shake_pin_frame()

        if PIN_ATTEMPTS >= 3:
            status_label.config(text="Too many incorrect attempts.")
            root.after(260, exit_app)
        else:
            status_label.config(text="Incorrect PIN")
            messagebox.showerror("Access denied", "Incorrect PIN")

    buttons = tk.Frame(card, bg=PANEL)
    buttons.place(relx=0.5, y=158, anchor="n")

    tk.Button(
        buttons, text="CONFIRM", command=confirm_pin,
        font=("Segoe UI", 10, "bold"), bg="#15934D", fg=WHITE,
        activebackground="#117A3E", activeforeground=WHITE,
        relief="flat", cursor="hand2", padx=25, pady=8
    ).pack(side="left", padx=7)

    tk.Button(
        buttons, text="EXIT", command=exit_app,
        font=("Segoe UI", 10, "bold"), bg="#A83245", fg=WHITE,
        activebackground="#8E2939", activeforeground=WHITE,
        relief="flat", cursor="hand2", padx=25, pady=8
    ).pack(side="left", padx=7)

    pin_entry.bind("<Return>", lambda event: confirm_pin())
    pin_entry.focus_set()



root.protocol("WM_DELETE_WINDOW", exit_app)
root.bind("<Escape>", handle_escape)
root.bind("<F11>", lambda event: toggle_fullscreen())

# Keep the application silent on the PIN screen. After three launches
# following the first successful PIN entry, open the home screen directly.
if should_skip_pin():
    initialize_music()
    home_screen()
else:
    pin_screen()
root.mainloop()
