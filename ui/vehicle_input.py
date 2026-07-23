import customtkinter as ctk


class VehicleInput(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent)


        self.vehicle_list = [
            "Car",
            "Bus",
            "Taxi",
            "Ambulance",
            "Fire Truck",
            "Police"
        ]


        label = ctk.CTkLabel(
            self,
            text="🚗 Vehicle Type",
            font=("Arial", 16, "bold")
        )

        label.pack(
            anchor="w",
            padx=10
        )


        self.vehicle = ctk.CTkComboBox(
            self,
            values=self.vehicle_list,
            width=300,
            height=35
        )

        self.vehicle.pack(
            fill="x",
            padx=10,
            pady=5
        )


    def get_value(self):
        return self.vehicle.get()