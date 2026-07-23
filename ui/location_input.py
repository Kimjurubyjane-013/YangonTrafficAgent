import customtkinter as ctk


class LocationInput(ctk.CTkFrame):

    def __init__(self, parent, title, placeholder):
        super().__init__(parent)


        self.locations = [
            "Hledan Junction",
            "Sule Pagoda",
            "Yangon General Hospital",
            "Junction Square",
            "Inya Lake",
            "Yangon Airport",
            "Myanmar Plaza",
            "Yangon Central Station"
        ]


        # Title
        label = ctk.CTkLabel(
            self,
            text=title,
            font=("Arial", 16, "bold")
        )

        label.pack(
            anchor="w",
            padx=10
        )


        # ComboBox
        self.location = ctk.CTkComboBox(
            self,
            values=self.locations,
            width=300,
            height=35
        )

        self.location.set(placeholder)

        self.location.pack(
            fill="x",
            padx=10,
            pady=5
        )


    def get_value(self):
        value = self.location.get()

        if value.startswith("Search"):
            return ""

        return value