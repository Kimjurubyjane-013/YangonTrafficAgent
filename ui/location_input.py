import customtkinter as ctk


class LocationInput(ctk.CTkFrame):

    def __init__(self, parent, title, placeholder):
        super().__init__(parent, fg_color="transparent")

        self.placeholder = placeholder

        self.locations = [
            "Hledan Junction", "Sule Pagoda", "Yangon General Hospital",
            "Junction Square", "Inya Lake", "Yangon Airport",
            "Myanmar Plaza", "Yangon Central Station"
        ]

        if title:
            label = ctk.CTkLabel(self, text=title, font=("Arial", 16, "bold"))
            label.pack(anchor="w", padx=10)

        self.location = ctk.CTkComboBox(
            self, values=self.locations, width=300, height=35,
            command=self.on_select
        )

        self.location.set(self.placeholder)
        self.location.pack(fill="x", padx=10, pady=5)

        self.entry = self.location._entry
        self.entry.bind("<FocusIn>", self.on_focus_in)
        self.entry.bind("<FocusOut>", self.on_focus_out)

    def on_focus_in(self, event=None):
        if self.location.get() == self.placeholder:
            self.location.set("")

    def on_focus_out(self, event=None):
        if not self.location.get().strip():
            self.location.set(self.placeholder)

    def on_select(self, choice):
        self.location.set(choice)

    def get_value(self):
        value = self.location.get().strip()
        if not value or value == self.placeholder:
            return ""
        return value

    def reset(self):
        self.location.set(self.placeholder)