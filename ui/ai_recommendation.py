import customtkinter as ctk


class AIRecommendation(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, corner_radius=15)

        self.default_text = "Waiting for route analysis..."

        title = ctk.CTkLabel(
            self, text="🤖 AI Traffic Assistant", font=("Arial", 22, "bold")
        )
        title.pack(pady=10)

        self.text_box = ctk.CTkTextbox(
            self, height=70, font=("Arial", 15), wrap="word"
        )
        self.text_box.pack(fill="x", padx=20, pady=(0, 15))

        self.text_box.insert("0.0", self.default_text)
        self.text_box.configure(state="disabled")

    def update_text(self, message):
        self.text_box.configure(state="normal")
        self.text_box.delete("0.0", "end")
        self.text_box.insert("0.0", message)
        self.text_box.configure(state="disabled")

    def reset(self):
        self.update_text(self.default_text)