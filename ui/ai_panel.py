import customtkinter as ctk


class AIPanel(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent)


        title = ctk.CTkLabel(
            self,
            text="🤖 AI Decision",
            font=("Arial", 22, "bold")
        )

        title.pack(pady=15)


        self.result = ctk.CTkTextbox(
            self,
            height=120,
            font=("Arial", 16)
        )

        self.result.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )


        self.result.insert(
            "end",
            "Waiting for traffic analysis..."
        )