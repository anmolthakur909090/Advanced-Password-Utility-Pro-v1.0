# Developed by Anmol Thakur (PGD202573050) Shoolini University (MCA-AI)
# Before running this code open your terminal or command prompt and run:
# pip install customtkinter (Modern UI/UX)
# pip install customtkinter qrcode[pil] cryptography requests pillow (AES-256 Vault, QR Codes)

import secrets
import string
import math
import hashlib
import base64
import requests
import qrcode
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Cryptography for Encrypted Vault
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ---------- Config & Dictionaries ----------
MAX_HISTORY = 50
CLIPBOARD_TIMEOUT = 30000
ENTROPY_WEAK = 40
ENTROPY_STRONG = 70

# Short wordlist for Passphrase mode (In a real app, load from a large txt file like EFF list)
WORDLIST = ["apple", "battery", "horse", "stapler", "ocean", "mountain", "guitar", "planet", 
            "shadow", "river", "rocket", "window", "forest", "desert", "silver", "gold", 
            "coffee", "dragon", "wizard", "castle", "quantum", "galaxy", "velvet", "thunder", 
            "phoenix", "crystal", "sunset", "breeze", "whisper", "echo", "neon", "puzzle"]

# ---------- Tooltip Helper ----------
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, fg_color="#333333", text_color="white", corner_radius=6, padx=10, pady=5)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# ---------- Application Class ----------
class PasswordUtilityApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Advanced Password Utility Pro v1.0")
        
        # Dimensions
        self.geometry("950x800")
        self.resizable(True, True) 
        
        try:
            self.state("zoomed")
        except Exception:
            pass 

        # Variables
        self.password_var = ctk.StringVar()
        self.length_var = ctk.IntVar(value=16)
        self.word_count_var = ctk.IntVar(value=4)
        self.status_var = ctk.StringVar(value="")
        self.mode_var = ctk.StringVar(value="Characters") 
        
        self.use_lower = ctk.BooleanVar(value=True)
        self.use_upper = ctk.BooleanVar(value=True)
        self.use_digits = ctk.BooleanVar(value=True)
        self.use_symbols = ctk.BooleanVar(value=True)
        self.exclude_ambiguous = ctk.BooleanVar(value=False)
        
        self.is_hidden = False
        self.clipboard_timer = None
        self.status_timer = None

        self._setup_ui()
        self.generate_password()

    def _setup_ui(self):
        # Configure Grid Layout - Row 0 for Main Content and Row 1 for the Footer
        self.grid_columnconfigure(0, weight=3, pad=10)
        self.grid_columnconfigure(1, weight=2, pad=10)
        self.grid_rowconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=0) 

        # ----- Left Panel (Controls) -----
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))

        # Header
        ctk.CTkLabel(left_frame, text="Advanced Password Utility", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(0, 2))
        
        # FIX: Added adaptive tuple ("black", "white") so it shows up correctly in Light Mode
        ctk.CTkLabel(left_frame, text="Developed by Anmol Thakur (PGD202573050) Shoolini University (MCA-AI)", font=ctk.CTkFont(size=13, weight="bold"), text_color=("black", "white")).pack(anchor="w", pady=(0, 20))

        # Mode Switcher (Characters vs Passphrase)
        self.mode_seg = ctk.CTkSegmentedButton(left_frame, values=["Characters", "Passphrase"], variable=self.mode_var, command=self.toggle_mode_ui)
        self.mode_seg.pack(fill="x", pady=(0, 15))

        # Password Display
        pwd_container = ctk.CTkFrame(left_frame, fg_color="transparent")
        pwd_container.pack(fill="x", pady=(0, 15))
        
        self.entry = ctk.CTkEntry(pwd_container, textvariable=self.password_var, font=ctk.CTkFont(family="Courier", size=18), state="readonly", height=45)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_toggle_vis = ctk.CTkButton(pwd_container, text="👁️", width=45, height=45, command=self.toggle_visibility, fg_color="transparent", border_width=1, text_color=("black", "white"))
        self.btn_toggle_vis.pack(side="right")

        # Action Buttons (Row 1)
        btn_row_1 = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_row_1.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(btn_row_1, text="🎲 Generate", command=self.generate_password, height=40, font=ctk.CTkFont(weight="bold")).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(btn_row_1, text="📋 Copy", command=lambda: self.copy_to_clipboard(self.password_var.get()), height=40, fg_color="#2b2b2b", hover_color="#404040").pack(side="left", expand=True, fill="x", padx=(5, 5))
        ctk.CTkButton(btn_row_1, text="💾 Encrypted Save", command=self.save_encrypted_vault, height=40, fg_color="#2a9d55", hover_color="#1e753f").pack(side="left", expand=True, fill="x", padx=(5, 0))

        # Action Buttons (Row 2 - Advanced)
        btn_row_2 = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_row_2.pack(fill="x", pady=(0, 20))

        ctk.CTkButton(btn_row_2, text="📱 Share via QR", command=self.show_qr_code, height=35, fg_color="#8e44ad", hover_color="#6c3483").pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(btn_row_2, text="🛡️ Check Data Breaches", command=self.check_pwned, height=35, fg_color="#d35400", hover_color="#a04000").pack(side="left", expand=True, fill="x", padx=(5, 0))

        # --- Dynamic Config Area ---
        self.config_frame = ctk.CTkFrame(left_frame)
        self.config_frame.pack(fill="x", pady=(0, 15), ipadx=10, ipady=10)
        
        # Length Slider
        self.slider_label = ctk.CTkLabel(self.config_frame, text="Password Length:", font=ctk.CTkFont(weight="bold"))
        self.slider_label.pack(anchor="w", padx=10, pady=(10, 0))
        
        slider_row = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        slider_row.pack(fill="x", padx=10, pady=(5, 10))
        
        self.slider = ctk.CTkSlider(slider_row, from_=4, to=64, variable=self.length_var, command=self._force_int_slider)
        self.slider.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.len_entry = ctk.CTkEntry(slider_row, textvariable=self.length_var, width=50, justify="center")
        self.len_entry.pack(side="right")

        # Character Rules (Hides in Passphrase mode)
        self.opts_frame = ctk.CTkFrame(left_frame)
        self.opts_frame.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10)
        
        ctk.CTkLabel(self.opts_frame, text="Character Types", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 10))
        
        ctk.CTkCheckBox(self.opts_frame, text="Lowercase (a-z)", variable=self.use_lower).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkCheckBox(self.opts_frame, text="Uppercase (A-Z)", variable=self.use_upper).grid(row=1, column=1, sticky="w", padx=10, pady=5)
        ctk.CTkCheckBox(self.opts_frame, text="Numbers (0-9)", variable=self.use_digits).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkCheckBox(self.opts_frame, text="Symbols (!@#$)", variable=self.use_symbols).grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        ambig_cb = ctk.CTkCheckBox(self.opts_frame, text="Exclude Ambiguous", variable=self.exclude_ambiguous)
        ambig_cb.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(15, 5))
        ToolTip(ambig_cb, "Removes confusing characters like '1', 'l', 'I', '0', and 'O'")

        # Strength Meter
        strength_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        strength_frame.pack(fill="x", pady=(10, 0))
        
        self.strength_label = ctk.CTkLabel(strength_frame, text="Strength: —", font=ctk.CTkFont(weight="bold"))
        self.strength_label.pack(anchor="w")
        
        self.strength_bar = ctk.CTkProgressBar(strength_frame, height=12)
        self.strength_bar.set(0)
        self.strength_bar.pack(fill="x", pady=(5, 5))

        self.status_label = ctk.CTkLabel(left_frame, textvariable=self.status_var, text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.pack(anchor="w", pady=(5, 10))

        # ----- Right Panel (History) -----
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=(20, 10))

        header_row = ctk.CTkFrame(right_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(header_row, text="Generation History", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(header_row, text="Clear", command=self.clear_history, width=50, height=24, fg_color="#cc4444", hover_color="#a83232").pack(side="right")
        
        ctk.CTkLabel(right_frame, text="Click any password to copy it", font=ctk.CTkFont(size=11), text_color="gray").pack(padx=15, anchor="w")

        self.history_scroll = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        self.history_scroll.pack(fill="both", expand=True, padx=5, pady=10)
        
        self.history_items = [] 

        # ----- Bottom Footer Panel (Project Description) -----
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))

        desc_text = ("Description: The Advanced Password Utility (Pro Edition), developed by Anmol Thakur (MCA-AI, Shoolini University), "
                     "is a comprehensive cybersecurity application designed to address modern authentication vulnerabilities. Built entirely "
                     "in Python with a focus on modern user experience and cryptographic security. To ensure end-to-end security, the application "
                     "integrates an AES-256 encrypted local vault, allowing users to safely store credentials without relying on vulnerable "
                     "plain-text files or third-party cloud servers. Furthermore, the utility tackles proactive threat intelligence by integrating "
                     "the Have I Been Pwned (HIBP) API. Combined with a responsive, modern graphical interface (CustomTkinter) and air-gapped "
                     "cross-device sharing via dynamic QR codes, this project serves as a robust, privacy-first alternative to commercial "
                     "password management solutions.")
        
        # FIX: Added adaptive tuple ("black", "white") so it shows up correctly in Light Mode
        ctk.CTkLabel(bottom_frame, text=desc_text, font=ctk.CTkFont(size=11, slant="italic", weight="bold"), text_color=("black", "white"), justify="left", wraplength=900).pack(pady=10)

    # ---------- Core Logic ----------
    def toggle_mode_ui(self, value):
        if value == "Passphrase":
            self.opts_frame.pack_forget()
            self.slider_label.configure(text="Number of Words:")
            self.slider.configure(from_=3, to=12, variable=self.word_count_var)
            self.len_entry.configure(textvariable=self.word_count_var)
        else:
            self.opts_frame.pack(fill="x", pady=(0, 20), ipadx=10, ipady=10, before=self.status_label.master.winfo_children()[-3])
            self.slider_label.configure(text="Password Length:")
            self.slider.configure(from_=4, to=64, variable=self.length_var)
            self.len_entry.configure(textvariable=self.length_var)
        self.generate_password()

    def _force_int_slider(self, value):
        if self.mode_var.get() == "Characters":
            self.length_var.set(int(value))
        else:
            self.word_count_var.set(int(value))

    def toggle_visibility(self):
        self.is_hidden = not self.is_hidden
        self.entry.configure(show="*" if self.is_hidden else "")
        self.btn_toggle_vis.configure(text="🔒" if self.is_hidden else "👁️")

    def generate_password(self):
        pwd = ""
        charset_size = 0

        if self.mode_var.get() == "Passphrase":
            count = self.word_count_var.get()
            words = [secrets.choice(WORDLIST) for _ in range(count)]
            pwd = "-".join(words)
            charset_size = len(WORDLIST)
            entropy = count * math.log2(charset_size)
        else:
            chars = ""
            guaranteed_chars = []
            ambiguous = "l1IO0" if self.exclude_ambiguous.get() else ""

            lower_pool = [c for c in string.ascii_lowercase if c not in ambiguous]
            upper_pool = [c for c in string.ascii_uppercase if c not in ambiguous]
            digit_pool = [c for c in string.digits if c not in ambiguous]
            symbol_pool = [c for c in string.punctuation if c not in ambiguous]

            if self.use_lower.get() and lower_pool:
                chars += "".join(lower_pool)
                guaranteed_chars.append(secrets.choice(lower_pool))
            if self.use_upper.get() and upper_pool:
                chars += "".join(upper_pool)
                guaranteed_chars.append(secrets.choice(upper_pool))
            if self.use_digits.get() and digit_pool:
                chars += "".join(digit_pool)
                guaranteed_chars.append(secrets.choice(digit_pool))
            if self.use_symbols.get() and symbol_pool:
                chars += "".join(symbol_pool)
                guaranteed_chars.append(secrets.choice(symbol_pool))

            if not chars:
                messagebox.showwarning("Warning", "Select at least one character type.")
                return

            length = max(self.length_var.get(), len(guaranteed_chars))
            self.length_var.set(length)

            remaining_length = length - len(guaranteed_chars)
            random_chars = [secrets.choice(chars) for _ in range(remaining_length)]
            pwd_list = guaranteed_chars + random_chars
            secrets.SystemRandom().shuffle(pwd_list)
            pwd = "".join(pwd_list)
            
            charset_size = len(chars)
            entropy = len(pwd) * math.log2(charset_size)

        self.entry.configure(state="normal")
        self.password_var.set(pwd)
        self.entry.configure(state="readonly")

        self.update_strength(entropy)
        self.add_to_history(pwd)

    def update_strength(self, entropy):
        if entropy < ENTROPY_WEAK:
            label, color, val = "Weak", "#cc4444", 0.3
        elif entropy < ENTROPY_STRONG:
            label, color, val = "Moderate", "#cc9900", 0.6
        else:
            label, color, val = "Strong", "#2a9d55", 1.0

        self.strength_label.configure(text=f"Strength: {label} ({entropy:.0f} bits)", text_color=color)
        self.strength_bar.set(val)
        self.strength_bar.configure(progress_color=color)

    # ---------- Advanced Features ----------

    def check_pwned(self):
        pwd = self.password_var.get()
        if not pwd: return
        
        self.show_status("Checking dark web databases...")
        self.update() # Force UI update
        
        # k-Anonymity SHA1 hashing
        sha1_pwd = hashlib.sha1(pwd.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1_pwd[:5], sha1_pwd[5:]
        
        try:
            url = f"https://api.pwnedpasswords.com/range/{prefix}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                hashes = (line.split(':') for line in response.text.splitlines())
                for h, count in hashes:
                    if h == suffix:
                        messagebox.showwarning("Pwned!", f"⚠️ Danger! This password has been seen in data breaches {count} times.\nDo not use it!")
                        self.show_status("⚠️ Password is compromised!")
                        return
                
                messagebox.showinfo("Safe", "✅ Good news! This password was not found in any known data breaches.")
                self.show_status("✅ Password appears safe")
            else:
                self.show_status("Error checking database.")
        except Exception as e:
            self.show_status("Failed to connect to HIBP API.")

    def show_qr_code(self):
        pwd = self.password_var.get()
        if not pwd: return

        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(pwd)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        
        # Create Popup Window
        qr_window = ctk.CTkToplevel(self)
        qr_window.title("Scan to Mobile")
        qr_window.geometry("350x400")
        qr_window.resizable(False, False)
        qr_window.attributes('-topmost', 'true') # Keep on top

        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(300, 300))
        ctk.CTkLabel(qr_window, text="", image=ctk_img).pack(pady=20)
        ctk.CTkLabel(qr_window, text="Scan with your smartphone camera", font=ctk.CTkFont(weight="bold")).pack()

    def save_encrypted_vault(self):
        if not self.history_items:
            messagebox.showinfo("Empty", "No passwords to save.")
            return

        dialog = ctk.CTkInputDialog(text="Create a Master Password for this Vault:", title="Encrypt Vault")
        master_pwd = dialog.get_input()
        
        if not master_pwd:
            self.show_status("Save cancelled.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".enc", filetypes=[("Encrypted Vault", "*.enc")], initialfile="MyPasswords.enc")
        if not path: return

        try:
            # Generate Cryptographic Key from Master Password
            salt = secrets.token_bytes(16)
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
            key = base64.urlsafe_b64encode(kdf.derive(master_pwd.encode()))
            f = Fernet(key)

            # Prepare data
            data = "\n".join(self.history_items).encode()
            encrypted_data = f.encrypt(data)

            # Save salt + encrypted data
            with open(path, "wb") as file:
                file.write(salt + encrypted_data)

            self.show_status("🔒 Vault encrypted and saved successfully")
            messagebox.showinfo("Success", "Vault Saved!\nYou will need your Master Password to read this file via decryption script later.")
        except Exception as e:
            messagebox.showerror("Encryption Error", str(e))

    # ---------- History & Clipboard ----------
    def add_to_history(self, pwd):
        self.history_items.insert(0, pwd)
        btn = ctk.CTkButton(
            self.history_scroll, text=pwd, font=ctk.CTkFont(family="Courier", size=14),
            fg_color="transparent", text_color=("black", "white"), hover_color=("#e0e0e0", "#333333"),
            anchor="w", command=lambda p=pwd: self.copy_to_clipboard(p)
        )
        btn.pack(fill="x", pady=2)
        
        if len(self.history_items) > MAX_HISTORY:
            self.history_items.pop()
            widgets = self.history_scroll.winfo_children()
            if widgets: widgets[-1].destroy()

    def clear_history(self):
        self.history_items.clear()
        for widget in self.history_scroll.winfo_children(): widget.destroy()
        self.show_status("History cleared")

    def copy_to_clipboard(self, text):
        if not text: return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.show_status("✅ Copied to clipboard! (Clears in 30s)")
        if self.clipboard_timer: self.after_cancel(self.clipboard_timer)
        self.clipboard_timer = self.after(CLIPBOARD_TIMEOUT, self.clear_clipboard)

    def clear_clipboard(self):
        self.clipboard_clear()
        self.show_status("Clipboard cleared for security")

    def show_status(self, msg):
        self.status_var.set(msg)
        if self.status_timer: self.after_cancel(self.status_timer)
        self.status_timer = self.after(3000, lambda: self.status_var.set(""))

if __name__ == "__main__":
    app = PasswordUtilityApp()
    app.mainloop()