import customtkinter as ctk

class Settings(ctk.CTkFrame):
    def __init__(self, master, tariff_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.tariff_manager = tariff_manager

        # --- Tabview for better organization ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        # Tabs
        self.tab_rates = self.tabview.add("Base Tariffs")
        self.tab_params = self.tabview.add("Advanced Parameters")
        self.tab_epias = self.tabview.add("EPİAŞ Integration")

        self._init_rates_tab()
        self._init_params_tab()
        self._init_epias_tab()

    def _init_rates_tab(self):
        """Standard Day/Peak/Night Rates"""
        frame = self.tab_rates
        
        self.rate_entries = {}
        row = 0
        
        lbl_info = ctk.CTkLabel(frame, text="Set standard time-of-use tariff rates (TL/kWh):", font=("Arial", 12))
        lbl_info.grid(row=row, column=0, columnspan=2, padx=10, pady=(10, 20), sticky="w")
        row += 1

        for name, rate in self.tariff_manager.rates.items():
            lbl = ctk.CTkLabel(frame, text=f"{name.capitalize()} Rate:")
            lbl.grid(row=row, column=0, padx=10, pady=5, sticky="w")
            
            ent = ctk.CTkEntry(frame)
            ent.insert(0, str(rate))
            ent.grid(row=row, column=1, padx=10, pady=5)
            
            self.rate_entries[name] = ent
            row += 1

        self.btn_save_rates = ctk.CTkButton(frame, text="Save Rates", command=self.save_rates)
        self.btn_save_rates.grid(row=row, column=1, pady=20, sticky="e")
        
        self.lbl_rates_status = ctk.CTkLabel(frame, text="", text_color="green")
        self.lbl_rates_status.grid(row=row+1, column=0, columnspan=2, pady=5)

    def _init_params_tab(self):
        """Advanced parameters matching the user's Excel sheet image."""
        frame = self.tab_params
        
        # Grid Setup
        frame.grid_columnconfigure(1, weight=1)
        
        self.param_entries = {}
        
        # List of parameters to display
        # (Label Text, Key in TariffManager.params, is_percentage)
        fields = [
            ("YEKDEM Tahmini (TL)", "yekdem_tahmini", False),
            ("İlave Katsayı (%)", "ilave_katsayi", True),
            ("Dengesizlik Oranı", "dengesizlik_orani", False),
            ("Dağıtım Bedeli (TL)", "dagitim_bedeli", False),
            ("BTV (%)", "btv", True),
            ("TRT (%)", "trt", True),
            ("Enerji Fonu (%)", "enerji_fonu", True),
            ("KDV (%)", "kdv", True),
            ("Profil Maliyeti", "profil_maliye", False)
        ]

        row = 0
        for label_text, key, is_pct in fields:
            lbl = ctk.CTkLabel(frame, text=label_text)
            lbl.grid(row=row, column=0, padx=10, pady=5, sticky="w")
            
            # Use yellow-ish fg_color to indicate editable input like the excel
            ent = ctk.CTkEntry(frame, fg_color="#4d4d20" if "katsayi" in key or "yekdem" in key else None)
            
            val = self.tariff_manager.params.get(key, 0.0)
            if is_pct:
                val = val * 100 # Display as percentage (e.g., 0.01 -> 1.0)
                
            ent.insert(0, f"{val:.5g}") # General float formatting
            ent.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
            
            self.param_entries[key] = (ent, is_pct)
            row += 1

        self.btn_save_params = ctk.CTkButton(frame, text="Save Parameters", command=self.save_params, fg_color="#F0A30A", hover_color="#D08208", text_color="black")
        self.btn_save_params.grid(row=row, column=1, pady=20, sticky="e")

        self.lbl_params_status = ctk.CTkLabel(frame, text="", text_color="green")
        self.lbl_params_status.grid(row=row+1, column=0, columnspan=2, pady=5)

    def _init_epias_tab(self):
        """EPİAŞ Integration Inputs"""
        frame = self.tab_epias
        
        ctk.CTkLabel(frame, text="EPİAŞ Credentials (Private)", font=("Roboto", 14, "bold")).pack(pady=10, padx=10, anchor="w")
        
        cred_frame = ctk.CTkFrame(frame)
        cred_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(cred_frame, text="Email:").grid(row=0, column=0, padx=10, pady=5)
        self.entry_email = ctk.CTkEntry(cred_frame, width=250)
        self.entry_email.grid(row=0, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(cred_frame, text="Password:").grid(row=1, column=0, padx=10, pady=5)
        self.entry_pass = ctk.CTkEntry(cred_frame, width=250, show="*")
        self.entry_pass.grid(row=1, column=1, padx=10, pady=5)

        self.btn_fetch = ctk.CTkButton(frame, text="Fetch Prices (eptr2)", command=self.fetch_web, fg_color="#E04F5F", hover_color="#C03F4F")
        self.btn_fetch.pack(pady=10, padx=10, fill="x")
        
        self.btn_login = ctk.CTkButton(frame, text="Test Login (Playwright)", command=self.test_login)
        self.btn_login.pack(pady=5, padx=10, fill="x")
        
        self.status_lbl = ctk.CTkLabel(frame, text="", text_color="green")
        self.status_lbl.pack(pady=10)

    def save_rates(self):
        try:
            day = float(self.rate_entries["day"].get())
            peak = float(self.rate_entries["peak"].get())
            night = float(self.rate_entries["night"].get())
            
            self.tariff_manager.update_rates(day, peak, night)
            self.lbl_rates_status.configure(text="Rates updated & saved!", text_color="green")
        except ValueError:
            self.lbl_rates_status.configure(text="Invalid number format.", text_color="red")

    def save_params(self):
        updates = {}
        try:
            for key, (ent, is_pct) in self.param_entries.items():
                val_str = ent.get()
                val = float(val_str)
                if is_pct:
                    val = val / 100.0 # Convert back to decimal
                updates[key] = val
            
            self.tariff_manager.update_params(**updates)
            self.lbl_params_status.configure(text="Parameters updated & saved!", text_color="green")
        except ValueError:
            self.lbl_params_status.configure(text="Invalid input. Use dots for decimals.", text_color="red")

    def fetch_web(self):
        # Get credentials from UI
        email = self.entry_email.get()
        pwd = self.entry_pass.get()
        
        if not email or not pwd:
            self.status_lbl.configure(text="Enter EPİAŞ Email/Pass first.", text_color="red")
            return

        # Trigger the real fetch
        self.status_lbl.configure(text="Fetching from EPİAŞ...", text_color="orange")
        self.update() # Force refresh
        
        # Pass credentials to manager -> service
        success = self.tariff_manager.fetch_prices_from_web(username=email, password=pwd)
        
        if success:
            self.status_lbl.configure(text="Fetched latest market rates!", text_color="blue")
            # Update UI entries in Rates Tab
            for name, rate in self.tariff_manager.rates.items():
                if name in self.rate_entries:
                    self.rate_entries[name].delete(0, "end")
                    self.rate_entries[name].insert(0, str(rate))
        else:
            self.status_lbl.configure(text="Failed to fetch (Check console).", text_color="red")

    def test_login(self):
        email = self.entry_email.get()
        pwd = self.entry_pass.get()
        if not email or not pwd:
            self.status_lbl.configure(text="Enter email and password.", text_color="red")
            return
            
        self.status_lbl.configure(text="Attempting login... (Browser will open)", text_color="orange")
        self.update()
        
        # Import from tariff
        from src.backend.tariff import EbiasService
        svc = EbiasService()
        success, msg = svc.automate_login(email, pwd)
        
        color = "blue" if success else "red"
        self.status_lbl.configure(text=msg, text_color=color)
