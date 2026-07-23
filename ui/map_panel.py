import customtkinter as ctk


class MapPanel(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=15
        )


        title = ctk.CTkLabel(
            self,
            text="🗺 Yangon Map",
            font=("Arial", 22, "bold")
        )

        title.pack(pady=20)


        map_text = ctk.CTkLabel(
            self,
            text="Map will appear here",
            font=("Arial", 30)
        )

        map_text.pack(
            expand=True
        )