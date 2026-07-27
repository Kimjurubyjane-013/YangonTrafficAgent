import customtkinter as ctk


class LocationInput(ctk.CTkFrame):

    def __init__(self, parent, title, placeholder):
        super().__init__(parent)

        self.placeholder = placeholder

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
            height=35,
            command=self.on_select
        )

        self.location.set(self.placeholder)

        self.location.pack(
            fill="x",
            padx=10,
            pady=5
        )

        # Underlying entry widget, used for focus/typing events
        self.entry = self.location._entry

        self.entry.bind(
            "<FocusIn>",
            self.on_focus_in
        )

        self.entry.bind(
            "<FocusOut>",
            self.on_focus_out
        )

        self.entry.bind(
            "<KeyRelease>",
            self.on_key_release
        )


    # =========================
    # Event Handlers
    # =========================

    def on_focus_in(self, event=None):

        if self.location.get() == self.placeholder:
            self.location.set("")

    def on_focus_out(self, event=None):

        if not self.location.get().strip():
            self.location.set(self.placeholder)

    def on_key_release(self, event=None):

        # If user has cleared the text manually, keep it empty
        # (placeholder only re-appears on focus out, not while typing)
        pass

    def on_select(self, choice):

        # Selecting from the dropdown list should behave the
        # same as typing a valid value
        self.location.set(choice)


    # =========================
    # Value Access
    # =========================

    def get_value(self):
        value = self.location.get().strip()

        if not value or value == self.placeholder:
            return ""

        return value