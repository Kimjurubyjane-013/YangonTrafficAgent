import customtkinter as ctk
import traceback

from ui.vehicle_input import VehicleInput
from ui.location_input import LocationInput
from algorithms.route_optimizer import find_optimal_route
from algorithms.vehicle import format_duration


class ControlPanel(ctk.CTkScrollableFrame):

    def __init__(self, parent, command):

        super().__init__(
            parent,
            width=380
        )

        self.command = command


        # =========================
        # Title
        # =========================

        title = ctk.CTkLabel(
            self,
            text="🚦 Route Request",
            font=("Arial", 22, "bold")
        )

        title.pack(
            pady=20
        )


        # =========================
        # Vehicle
        # =========================

        self.vehicle = VehicleInput(self)

        self.vehicle.pack(
            fill="x",
            padx=20,
            pady=10
        )


        # =========================
        # Start Point
        # =========================

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


        # =========================
        # Destination
        # =========================

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


        # =========================
        # Button
        # =========================

        button = ctk.CTkButton(
            self,
            text="Find Optimal Route",
            command=self.send_request,
            width=300,
            height=45,
            font=("Arial", 15, "bold")
        )

        button.pack(
            pady=15
        )


        # =========================
        # Result Display
        # =========================

        result_title = ctk.CTkLabel(
            self,
            text="Route Result",
            font=("Arial", 16, "bold")
        )

        result_title.pack(
            pady=5
        )


        self.output_box = ctk.CTkTextbox(
            self,
            width=330,
            height=200,
            font=("Consolas", 13)
        )

        self.output_box.pack(
            padx=20,
            pady=10
        )



    # =========================
    # Send Route Request
    # =========================

    def send_request(self):

        try:

            vehicle = self.vehicle.get_value()
            start = self.start.get_value()
            destination = self.destination.get_value()


            if not start or not destination:

                self.show_result(
                    "Please select a valid start and destination "
                    "from the dropdown list."
                )

                return


            result = find_optimal_route(
                vehicle,
                start,
                destination
            )


            print("Route result:", result)


            # Display inside GUI
            self.show_result(result)


            # Send to main window if needed
            self.command(result)


        except ValueError as e:

            # Known, expected failure (e.g. no route exists)
            self.show_result(str(e))


        except Exception:

            traceback.print_exc()

            self.show_result(
                "Something went wrong while finding the route. "
                "Please try again."
            )



    # =========================
    # Display Result
    # =========================
    def show_result(self, result):

        self.output_box.delete(
            "1.0",
            "end"
        )


        if isinstance(result, dict):

            route = result.get("route") or []
            route_text = " → ".join(route) if route else "—"


            distance = result.get("distance")

            distance_text = (
                f"{distance:.1f} km"
                if distance is not None
                else "—"
            )


            time_text = (
                format_duration(result.get("time"))
                if result.get("time") is not None
                else "—"
            )


            traffic = result.get("traffic", "Unknown")


            text = f"""✅ Optimal Route Found


🚗 Vehicle
   {result.get("vehicle")}


🚦 Traffic Condition
   {traffic}


🛣️ Route
   {route_text}


📏 Distance
   {distance_text}


⏱️ Estimated Time
   {time_text}
"""


        else:

            text = f"⚠️ {result}"


        self.output_box.insert(
            "end",
            text
        )