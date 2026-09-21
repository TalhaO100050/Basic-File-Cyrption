import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

# --- ŞİFRELEME FONKSİYONLARI ---

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=300_000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_bytes(data: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data)
    return salt + encrypted

def decrypt_bytes(encrypted_data: bytes, password: str) -> bytes:
    salt = encrypted_data[:16]
    encrypted = encrypted_data[16:]
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    return fernet.decrypt(encrypted)

# --- SÜRÜKLE-BIRAK İÇİN CUSTOMTKINTER VE DND ENTEGRASYONU ---
class CustomCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

# --- ARAYÜZ (GUI) TASARIMI ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Normal ctk.CTk yerine kendi oluşturduğumuz CustomCTk sınıfını kullanıyoruz
class EncryptorApp(CustomCTk):
    def __init__(self):
        super().__init__()
        self.title("Dosya ve Yazı Şifreleyici")
        self.geometry("600x450")
        self.resizable(False, False)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_file = self.tabview.add("Dosya İşlemleri")
        self.tab_text = self.tabview.add("Yazı İşlemleri")

        self.setup_file_tab()
        self.setup_text_tab()

    # ------------------ DOSYA SEKMESİ ------------------
    def setup_file_tab(self):
        self.selected_file_path = ""

        self.lbl_drop = ctk.CTkLabel(self.tab_file, text="📁\nDosyayı Seçin veya Buraya Sürükleyin", 
                                     font=("Arial", 14), text_color="gray", width=400, height=80, 
                                     fg_color="#2b2b2b", corner_radius=10)
        self.lbl_drop.pack(pady=15)

        self.btn_select = ctk.CTkButton(self.tab_file, text="Dosya Seç", command=self.select_file)
        self.btn_select.pack(pady=5)

        self.lbl_file = ctk.CTkLabel(self.tab_file, text="Henüz dosya seçilmedi", text_color="gray")
        self.lbl_file.pack(pady=5)

        self.entry_pwd_file = ctk.CTkEntry(self.tab_file, placeholder_text="Şifre Giriniz", show="*", width=300)
        self.entry_pwd_file.pack(pady=15)

        self.frame_btn_file = ctk.CTkFrame(self.tab_file, fg_color="transparent")
        self.frame_btn_file.pack(pady=10)

        self.btn_enc_file = ctk.CTkButton(self.frame_btn_file, text="🔒 Şifrele", fg_color="#2FA572", hover_color="#1E6B49", command=self.encrypt_file_action)
        self.btn_enc_file.grid(row=0, column=0, padx=10)

        self.btn_dec_file = ctk.CTkButton(self.frame_btn_file, text="🔓 Şifreyi Çöz", fg_color="#E74C3C", hover_color="#962D22", command=self.decrypt_file_action)
        self.btn_dec_file.grid(row=0, column=1, padx=10)

        # Sürükle Bırak Etkinleştirmesi
        self.tab_file.drop_target_register(DND_FILES)
        self.tab_file.dnd_bind('<<Drop>>', self.handle_drop)
        
        self.lbl_drop.drop_target_register(DND_FILES)
        self.lbl_drop.dnd_bind('<<Drop>>', self.handle_drop)

    def handle_drop(self, event):
        # Windows'ta dosya yollarında boşluk varsa yol { } içine alınır. 
        # tk.splitlist() metodu bunu en güvenli şekilde ayıklar.
        dropped_files = self.tk.splitlist(event.data)
        if dropped_files:
            path = dropped_files[0] # Eğer birden fazla atılırsa sadece ilkini alır
            self.selected_file_path = path
            self.lbl_file.configure(text=os.path.basename(path), text_color="white")
            self.lbl_drop.configure(text="📁\nDosya Hazır", text_color="#2FA572")

    def select_file(self):
        path = filedialog.askopenfilename(title="İşlem Yapılacak Dosyayı Seçin")
        if path:
            self.selected_file_path = path
            self.lbl_file.configure(text=os.path.basename(path), text_color="white")
            self.lbl_drop.configure(text="📁\nDosya Hazır", text_color="#2FA572")

    def encrypt_file_action(self):
        pwd = self.entry_pwd_file.get()
        if not self.selected_file_path or not pwd:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir dosya seçin ve şifre girin.")
            return

        try:
            with open(self.selected_file_path, "rb") as f:
                data = f.read()

            encrypted_data = encrypt_bytes(data, pwd)

            save_path = filedialog.asksaveasfilename(title="Şifrelenmiş Dosyayı Kaydet")
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(encrypted_data)
                messagebox.showinfo("Başarılı", "Dosya başarıyla şifrelendi!")
                self.entry_pwd_file.delete(0, 'end')
        except Exception as e:
            messagebox.showerror("Hata", f"Bir sorun oluştu:\n{e}")

    def decrypt_file_action(self):
        pwd = self.entry_pwd_file.get()
        if not self.selected_file_path or not pwd:
            messagebox.showwarning("Eksik Bilgi", "Lütfen bir dosya seçin ve şifre girin.")
            return

        try:
            with open(self.selected_file_path, "rb") as f:
                data = f.read()

            decrypted_data = decrypt_bytes(data, pwd)

            save_path = filedialog.asksaveasfilename(title="Şifresi Çözülmüş Dosyayı Kaydet")
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(decrypted_data)
                messagebox.showinfo("Başarılı", "Dosya şifresi başarıyla çözüldü!")
                self.entry_pwd_file.delete(0, 'end')
        except Exception:
            messagebox.showerror("Hata", "Şifre yanlış veya dosya bozuk!")

    # ------------------ YAZI SEKMESİ ------------------
    def setup_text_tab(self):
        self.textbox_input = ctk.CTkTextbox(self.tab_text, height=80)
        self.textbox_input.pack(padx=20, pady=10, fill="x")
        self.textbox_input.insert("1.0", "Buraya şifrelenecek veya çözülecek metni girin...")

        self.entry_pwd_text = ctk.CTkEntry(self.tab_text, placeholder_text="Şifre Giriniz", show="*", width=300)
        self.entry_pwd_text.pack(pady=10)

        self.frame_btn_text = ctk.CTkFrame(self.tab_text, fg_color="transparent")
        self.frame_btn_text.pack(pady=10)

        self.btn_enc_text = ctk.CTkButton(self.frame_btn_text, text="🔒 Yazıyı Şifrele", fg_color="#2FA572", hover_color="#1E6B49", command=self.encrypt_text_action)
        self.btn_enc_text.grid(row=0, column=0, padx=10)

        self.btn_dec_text = ctk.CTkButton(self.frame_btn_text, text="🔓 Yazı Şifresini Çöz", fg_color="#E74C3C", hover_color="#962D22", command=self.decrypt_text_action)
        self.btn_dec_text.grid(row=0, column=1, padx=10)

        self.textbox_output = ctk.CTkTextbox(self.tab_text, height=80)
        self.textbox_output.pack(padx=20, pady=10, fill="x")

    def encrypt_text_action(self):
        pwd = self.entry_pwd_text.get()
        text = self.textbox_input.get("1.0", "end-1c").strip()

        if not text or not pwd or text.startswith("Buraya şifrelenecek"):
            messagebox.showwarning("Eksik Bilgi", "Lütfen metin ve şifre girin.")
            return

        try:
            data = text.encode("utf-8")
            encrypted_data = encrypt_bytes(data, pwd)
            b64_encoded = base64.b64encode(encrypted_data).decode('utf-8')
            
            self.textbox_output.delete("1.0", "end")
            self.textbox_output.insert("1.0", b64_encoded)
        except Exception as e:
            messagebox.showerror("Hata", f"Bir sorun oluştu:\n{e}")

    def decrypt_text_action(self):
        pwd = self.entry_pwd_text.get()
        text = self.textbox_input.get("1.0", "end-1c").strip()

        if not text or not pwd:
            messagebox.showwarning("Eksik Bilgi", "Lütfen şifreli metni ve şifreyi girin.")
            return

        try:
            raw_encrypted_bytes = base64.b64decode(text.encode('utf-8'))
            decrypted_data = decrypt_bytes(raw_encrypted_bytes, pwd)
            
            self.textbox_output.delete("1.0", "end")
            self.textbox_output.insert("1.0", decrypted_data.decode("utf-8"))
        except Exception:
            messagebox.showerror("Hata", "Şifre yanlış veya kopyalanan metin hatalı!")

if __name__ == "__main__":
    app = EncryptorApp()
    app.mainloop()