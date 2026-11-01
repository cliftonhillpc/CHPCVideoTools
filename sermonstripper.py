import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import vlc
import time
import os
import sys
import subprocess
from datetime import timedelta

class VideoScrubberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Scrubber & Clipper")
        self.root.geometry("1100x750")

        self.player = None
        self.instance = None
        self.media = None
        self.video_path = None
        self.is_playing = False
        self.start_time = 0.0
        self.end_time = 0.0
        self.slider_updating = False

        # ---- CLI options (defaults from your script) ----
        self.script_path = os.path.expanduser("~/Documents/ff_script3.py")          # change this to the real command/script
        self.opt_a = 2                            # fade in
        self.opt_b = 1                            # fade out
        self.opt_c = False                        # skip audio filters
        self.opt_d = False                        # no heuristic
        self.opt_e = 24                           # noise reduction
        self.opt_f = 20                           # amplification (dB)
        self.opt_g = False                        # keep work directory

        self.setup_ui()

    def setup_ui(self):
        # Top controls
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(top_frame, text="Load Video", command=self.load_video).pack(side=tk.LEFT, padx=5)
        self.play_btn = ttk.Button(top_frame, text="▶ Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="⏹ Stop", command=self.stop_video).pack(side=tk.LEFT, padx=5)

        ttk.Button(top_frame, text="Set Start", command=self.set_start).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Set End", command=self.set_end).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Save Times", command=self.save_times).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Options", command=self.open_options).pack(side=tk.LEFT, padx=5)

        # Video frame
        self.video_frame = tk.Frame(self.root, bg="black", relief=tk.SUNKEN, borderwidth=2)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.root.update_idletasks()

        vlc_options = [
            '--no-video-title-show',
            '--quiet',
            '--no-snapshot-preview',
            '--avcodec-hw=any',
        ]
        self.instance = vlc.Instance(' '.join(vlc_options))
        self.player = self.instance.media_player_new()

        self.root.after(100, self.embed_player)

        # Timeline
        slider_frame = ttk.Frame(self.root)
        slider_frame.pack(fill=tk.X, padx=10, pady=5)

        self.time_label = ttk.Label(slider_frame, text="00:00 / 00:00")
        self.time_label.pack(side=tk.LEFT, padx=5)

        self.slider = ttk.Scale(slider_frame, from_=0, to=1000, orient=tk.HORIZONTAL,
                                command=self.on_slider_move)
        self.slider.bind("<ButtonPress-1>", lambda e: setattr(self, 'slider_updating', True))
        self.slider.bind("<ButtonRelease-1>", lambda e: setattr(self, 'slider_updating', False))
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Info panel
        info_frame = ttk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=10, pady=8)

        self.start_label = ttk.Label(info_frame, text="Start: --:--")
        self.start_label.pack(side=tk.LEFT, padx=15)

        self.end_label = ttk.Label(info_frame, text="End: --:--")
        self.end_label.pack(side=tk.LEFT, padx=15)

        self.duration_label = ttk.Label(info_frame, text="")
        self.duration_label.pack(side=tk.RIGHT, padx=10)

        # Keyboard shortcuts
        self.root.bind("<space>", lambda e: self.toggle_play())

    def embed_player(self):
        try:
            if sys.platform.startswith('win'):
                self.player.set_hwnd(self.video_frame.winfo_id())
            elif sys.platform.startswith('darwin'):
                self.player.set_nsobject(self.video_frame.winfo_id())
            else:
                self.player.set_xwindow(self.video_frame.winfo_id())
        except Exception as e:
            messagebox.showerror("Embed Error", f"Failed to embed player:\n{e}")

    def load_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv"), ("All Files", "*.*")]
        )
        if not path:
            return

        self.video_path = path
        try:
            self.media = self.instance.media_new(self.video_path)
            self.player.set_media(self.media)

            self.player.play()
            time.sleep(0.6)
            self.player.pause()

            duration_ms = self.player.get_length()
            if duration_ms > 0:
                self.slider.config(to=duration_ms)
                dur_str = str(timedelta(milliseconds=duration_ms))[:-3]
                self.duration_label.config(text=f"Duration: {dur_str}")

            self.player.play()
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def toggle_play(self):
        if not self.player:
            return
        if self.player.is_playing():
            self.player.pause()
            self.play_btn.config(text="▶ Play")
        else:
            self.player.play()
            self.play_btn.config(text="⏸ Pause")

    def stop_video(self):
        if self.player:
            self.player.stop()
            self.play_btn.config(text="▶ Play")
            self.slider.set(0)

    def on_slider_move(self, val):
        if self.slider_updating:
            return
        if self.player and self.media:
            try:
                self.player.set_time(int(float(val)))
            except:
                pass

    def update_slider(self):
        if self.player:
            if self.player.is_playing():
                current_time = self.player.get_time()
                if current_time >= 0:
                    self.slider_updating = True
                    self.slider.set(current_time)
                    self.slider_updating = False

                    current_str = str(timedelta(milliseconds=current_time))[:-3]
                    total_ms = self.player.get_length()
                    total_str = str(timedelta(milliseconds=total_ms))[:-3] if total_ms > 0 else "??:??"
                    self.time_label.config(text=f"{current_str} / {total_str}")

        self.root.after(150, self.update_slider)

    def set_start(self):
        if self.player:
            self.start_time = self.player.get_time() / 1000.0
            self.start_label.config(text=f"Start: {str(timedelta(seconds=int(self.start_time)))}")

    def set_end(self):
        if self.player:
            self.end_time = self.player.get_time() / 1000.0
            self.end_label.config(text=f"End: {str(timedelta(seconds=int(self.end_time)))}")
            if self.end_time <= self.start_time and self.start_time > 0:
                messagebox.showwarning("Warning", "End time should be after Start time")

    def seconds_to_mmss(self, seconds):
        """Convert float seconds → MM:SS string"""
        total = int(round(seconds))
        mins = total // 60
        secs = total % 60
        return f"{mins:02d}:{secs:02d}"

    def open_options(self):
        """Options dialog for the CLI parameters"""
        win = tk.Toplevel(self.root)
        win.title("Processing Options")
        win.geometry("420x380")
        win.transient(self.root)
        win.grab_set()

        # Script path
        ttk.Label(win, text="Script / Command:").grid(row=0, column=0, sticky="w", padx=10, pady=6)
        script_var = tk.StringVar(value=self.script_path)
        ttk.Entry(win, textvariable=script_var, width=40).grid(row=0, column=1, columnspan=2, padx=10, pady=6)

        # Numeric options
        ttk.Label(win, text="Fade-in duration (-a):").grid(row=1, column=0, sticky="w", padx=10, pady=4)
        a_var = tk.IntVar(value=self.opt_a)
        ttk.Spinbox(win, from_=0, to=30, textvariable=a_var, width=8).grid(row=1, column=1, sticky="w", padx=10)

        ttk.Label(win, text="Fade-out duration (-b):").grid(row=2, column=0, sticky="w", padx=10, pady=4)
        b_var = tk.IntVar(value=self.opt_b)
        ttk.Spinbox(win, from_=0, to=30, textvariable=b_var, width=8).grid(row=2, column=1, sticky="w", padx=10)

        ttk.Label(win, text="Noise reduction (-e):").grid(row=3, column=0, sticky="w", padx=10, pady=4)
        e_var = tk.IntVar(value=self.opt_e)
        ttk.Spinbox(win, from_=0, to=100, textvariable=e_var, width=8).grid(row=3, column=1, sticky="w", padx=10)

        ttk.Label(win, text="Amplification dB (-f):").grid(row=4, column=0, sticky="w", padx=10, pady=4)
        f_var = tk.IntVar(value=self.opt_f)
        ttk.Spinbox(win, from_=0, to=60, textvariable=f_var, width=8).grid(row=4, column=1, sticky="w", padx=10)

        # Boolean flags
        c_var = tk.BooleanVar(value=self.opt_c)
        ttk.Checkbutton(win, text="Skip audio filters (-c)", variable=c_var).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=10, pady=6)

        d_var = tk.BooleanVar(value=self.opt_d)
        ttk.Checkbutton(win, text="Disable heuristic / start_time additions (-d)", variable=d_var).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=10, pady=4)

        g_var = tk.BooleanVar(value=self.opt_g)
        ttk.Checkbutton(win, text="Keep work directory (-g)", variable=g_var).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=10, pady=4)

        def save_options():
            self.script_path = script_var.get().strip()
            self.opt_a = a_var.get()
            self.opt_b = b_var.get()
            self.opt_c = c_var.get()
            self.opt_d = d_var.get()
            self.opt_e = e_var.get()
            self.opt_f = f_var.get()
            self.opt_g = g_var.get()
            win.destroy()

        ttk.Button(win, text="Save Options", command=save_options).grid(
            row=8, column=0, columnspan=2, pady=20)

    def save_times(self):
        if not self.video_path:
            messagebox.showwarning("Warning", "No video loaded")
            return
        if self.start_time == 0 and self.end_time == 0:
            messagebox.showwarning("Warning", "Please set Start and/or End times")
            return

        # Ask for output video file
        out_path = filedialog.asksaveasfilename(
            defaultextension=".mkv",
            filetypes=[
                ("Matroska Video", "*.mkv"),
                ("MP4 Video", "*.mp4"),
                ("All Files", "*.*")
            ],
            title="Choose output video filename"
        )
        if not out_path:
            return

        # Format times as MM:SS
        start_mmss = self.seconds_to_mmss(self.start_time)
        end_mmss = self.seconds_to_mmss(self.end_time)
	
        script = os.path.expanduser(self.script_path)

        # Build command
        cmd = [
	    "python3",
            script,
            self.video_path,
            out_path,
            start_mmss,
            end_mmss,
            "-a", str(self.opt_a),
            "-b", str(self.opt_b),
            "-e", str(self.opt_e),
            "-f", str(self.opt_f),
        ]
        if self.opt_c:
            cmd.append("-c")
        if self.opt_d:
            cmd.append("-d")
        if self.opt_g:
            cmd.append("-g")

        # ----- Live console window -----
        console = tk.Toplevel(self.root)
        console.title("Processing Console")
        console.geometry("800x500")
        console.transient(self.root)

        # Make it stay on top a bit
        console.attributes("-topmost", True)

        text = tk.Text(console, wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4",
                       font=("Consolas", 10), insertbackground="white")
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(console, orient=tk.VERTICAL, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scrollbar.set)

        # Status bar at the bottom
        status = ttk.Label(console, text="Starting...", relief=tk.SUNKEN, anchor=tk.W)
        status.pack(side=tk.BOTTOM, fill=tk.X)

        def append(msg, tag=None):
            text.insert(tk.END, msg)
            if tag:
                # simple colouring
                pass
            text.see(tk.END)
            console.update_idletasks()

        append(f"$ {' '.join(cmd)}\n\n")
        status.config(text="Running...")

        try:
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,   # merge stderr into stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Read output in a background thread so GUI stays responsive
            import threading

            def reader():
                try:
                    for line in process.stdout:
                        # Schedule GUI update on the main thread
                        self.root.after(0, lambda l=line: append(l))
                    process.wait()
                    code = process.returncode
                    self.root.after(0, lambda: finish(code))
                except Exception as e:
                    self.root.after(0, lambda: append(f"\n[Reader error] {e}\n"))

            def finish(code):
                if code == 0:
                    append("\n===== FINISHED SUCCESSFULLY =====\n")
                    status.config(text=f"Done (exit code 0) — Output: {out_path}")
                    messagebox.showinfo("Success", f"Processing finished.\n\nOutput:\n{out_path}", parent=console)
                else:
                    append(f"\n===== FAILED (exit code {code}) =====\n")
                    status.config(text=f"Failed (exit code {code})")
                    messagebox.showerror("Error", f"Script failed with exit code {code}", parent=console)

            thread = threading.Thread(target=reader, daemon=True)
            thread.start()

        except FileNotFoundError:
            append(f"ERROR: Could not find the script/command:\n{self.script_path}\n")
            status.config(text="Error: script not found")
            messagebox.showerror(
                "Error",
                f"Could not find the script/command:\n{self.script_path}\n\n"
                "Set the correct path in the Options window.",
                parent=console
            )
        except Exception as e:
            append(f"ERROR: {e}\n")
            status.config(text="Error")
            messagebox.showerror("Error", str(e), parent=console)

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoScrubberApp(root)
    root.after(200, app.update_slider)
    root.mainloop()
