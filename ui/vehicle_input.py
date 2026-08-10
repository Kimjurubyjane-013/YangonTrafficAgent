import customtkinter as ctk


class VehicleInput(ctk.CTkFrame):

    def __init__(self, parent, title="🚗 Vehicle Type"):
        super().__init__(parent, fg_color="transparent")

        self.default_value = "Car"

        self.vehicle_list = [
            "Car", "Bus", "Taxi", "Ambulance", "Fire Truck", "Police"
        ]

        if title:
            label = ctk.CTkLabel(self, text=title, font=("Arial", 16, "bold"))
            label.pack(anchor="w", padx=10)

        self.vehicle = ctk.CTkComboBox(
            self, values=self.vehicle_list, width=300, height=35
        )

        self.vehicle.set(self.default_value)
        self.vehicle.pack(fill="x", padx=10, pady=5)

    def get_value(self):
        return self.vehicle.get()

    def reset(self):
        self.vehicle.set(self.default_value)