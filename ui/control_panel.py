import customtkinter as ctk
import traceback
import subprocess
import sys

from ui.vehicle_input import VehicleInput
from ui.location_input import LocationInput


class ControlPanel(ctk.CTkScrollableFrame):

    def __init__(self, parent, command):

        super().__init__(parent, corner_radius=20)

        self.command = command
        self.last_result = None


        title = ctk.CTkLabel(
            self, text="🚦 Route Request", font=("Arial", 24, "bold")
        )
        title.pack(pady=(20, 15))

        subtitle = ctk.CTkLabel(
            self, text="Enter your travel information", font=("Arial", 14)
        )
        subtitle.pack(pady=(0, 15))


        vehicle_frame = ctk.CTkFrame(self, corner_radius=15)
        vehicle_frame.pack(fill="x", padx=20, pady=10)

        vehicle_label = ctk.CTkLabel(
            vehicle_frame, text="🚗 Vehicle Type", font=("Arial", 15, "bold")
        )
        vehicle_label.pack(anchor="w", padx=15, pady=(10, 5))

        self.vehicle = VehicleInput(vehicle_frame, title="")
        self.vehicle.pack(fill="x", padx=15, pady=(0, 10))


        location_frame = ctk.CTkFrame(self, corner_radius=15)
        location_frame.pack(fill="x", padx=20, pady=10)

        start_label = ctk.CTkLabel(
            location_frame, text="📍 Starting Point", font=("Arial", 15, "bold")
        )
        start_label.pack(anchor="w", padx=15, pady=(10, 5))

        self.start = LocationInput(location_frame, "", "Search Starting Point")
        self.start.pack(fill="x", padx=15, pady=(0, 10))

        destination_label = ctk.CTkLabel(
            location_frame, text="🎯 Destination", font=("Arial", 15, "bold")
        )
        destination_label.pack(anchor="w", padx=15, pady=(0, 5))

        self.destination = LocationInput(location_frame, "", "Search Destination Point")
        self.destination.pack(fill="x", padx=15, pady=(0, 15))


        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=30, pady=20)

        button_row.grid_columnconfigure(0, weight=4)
        button_row.grid_columnconfigure(1, weight=1)

        self.button = ctk.CTkButton(
            button_row, text="🔍 Find Optimal Route", command=self.send_request,
            height=45, font=("Arial", 16, "bold")
        )
        self.button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.reset_button = ctk.CTkButton(
            button_row, text="🔄 Reset", command=self.reset_all,
            height=45, font=("Arial", 16, "bold"),
            fg_color="gray40", hover_color="gray30"
        )
        self.reset_button.grid(row=0, column=1, sticky="ew")


        self.sim_button = ctk.CTkButton(
            self, text="🚘 Vehicle Route Simulation", command=self.open_simulation,
            height=40, font=("Arial", 14, "bold"),
            fg_color="#2E7D32", hover_color="#1B5E20"
        )
        self.sim_button.pack(fill="x", padx=30, pady=(0, 10))


        self.status = ctk.CTkLabel(self, text="Ready", font=("Arial", 14))
        self.status.pack(pady=10)


    def reset_all(self):

        self.vehicle.reset()
        self.start.reset()
        self.destination.reset()

        self.status.configure(text="Ready")
        self.last_result = None

        self.command({"reset": True})


    def send_request(self):

        try:

            vehicle = self.vehicle.get_value()
            start = self.start.get_value()
            destination = self.destination.get_value()

            if not start or not destination:
                self.status.configure(text="⚠️ Please select locations")
                return

            self.status.configure(text="🔍 Searching optimal route...")

            request = {
                "vehicle": vehicle,
                "start": start,
                "destination": destination
            }

            self.command(request)

        except Exception:
            traceback.print_exc()
            self.status.configure(text="❌ Error occurred")


    def set_last_result(self, result):
        self.last_result = result
        self.status.configure(text="✅ Route ready")


    def open_simulation(self):

        if not self.last_result:
            self.status.configure(text="⚠️ Find a route first")
            return

        subprocess.Popen([
            sys.executable,
            "simulation.py",
            self.last_result.get("vehicle", "Car"),
            str(self.last_result.get("distance", 5.0)),
            str(self.last_result.get("time", 10.0))
        ])