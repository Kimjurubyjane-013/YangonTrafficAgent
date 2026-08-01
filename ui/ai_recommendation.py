import customtkinter as ctk


class AIRecommendation(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=15
        )

        self.default_text = "Waiting for route analysis..."

        title = ctk.CTkLabel(
            self,
            text="🤖 AI Traffic Assistant",
            font=("Arial", 22, "bold")
        )

        title.pack(
            pady=10
        )


        self.text = ctk.CTkLabel(
            self,
            text=self.default_text,
            wraplength=400,
            font=("Arial", 15)
        )

        self.text.pack(
            padx=20,
            pady=20
        )


    def update_text(self, message):

        self.text.configure(
            text=message
        )


    def reset(self):

        self.text.configure(
            text=self.default_text
        )