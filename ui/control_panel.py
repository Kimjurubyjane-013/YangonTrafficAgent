import customtkinter as ctk

from ui.vehicle_input import VehicleInput
from ui.location_input import LocationInput


class ControlPanel(ctk.CTkFrame):

    def __init__(self, parent, command):

        super().__init__(
            parent,
            width=380
        )


        self.command = command

        self.pack_propagate(False)


        # Title
        title = ctk.CTkLabel(
            self,
            text="🚦 Route Request",
            font=("Arial", 22, "bold")
        )

        title.pack(
            pady=20
        )


        # Vehicle
        self.vehicle = VehicleInput(self)

        self.vehicle.pack(
            fill="x",
            padx=20,
            pady=10
        )


        # Start Point
        self.start = LocationInput(
            self,
            "📍 Start Point",
            "Search Starting Point"
        )

        self.start.pack(
            fill="x",
            padx=20,
            pady=10
        )


        # Destination
        self.destination = LocationInput(
            self,
            "🎯 Destination",
            "Search Destination Point"
        )

        self.destination.pack(
            fill="x",
            padx=20,
            pady=10
        )


        # Button
        button = ctk.CTkButton(
            self,
            text="Find Optimal Route",
            command=self.send_request,
            width=300,
            height=45,
            font=("Arial", 15, "bold")
        )


        button.pack(
            pady=30
        )


    def send_request(self):

        request = {

            "vehicle":
            self.vehicle.get_value(),

            "start":
            self.start.get_value(),

            "destination":
            self.destination.get_value()

        }


        print(request)


        self.command(request)