import customtkinter as ctk


class MapPanel(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(
            parent,
            corner_radius=15
        )


        title = ctk.CTkLabel(
            self,
            text="🗺 Yangon Route Map",
            font=("Arial", 22, "bold")
        )

        title.pack(
            pady=20
        )


        self.map_display = ctk.CTkTextbox(
            self,
            width=600,
            height=500,
            font=("Consolas", 15)
        )

        self.map_display.pack(
            expand=True,
            fill="both",
            padx=20,
            pady=20
        )


        self.show_default()



    def show_default(self):

        self.map_display.delete(
            "1.0",
            "end"
        )

        self.map_display.insert(
            "end",
            """
        Yangon Map Area
        
        Select start and destination
        to display the optimal route.
            """
        )



    def update_route(self, result):

        self.map_display.delete(
            "1.0",
            "end"
        )


        if not result:
            self.show_default()
            return


        route = result.get("route", [])


        route_text = "\n\n".join(
            [
                f"📍 {index + 1}. {location}"
                for index, location in enumerate(route)
            ]
        )


        display = f"""
🚦 Optimal Route Visualization


🚗 Vehicle:
{result.get('vehicle')}


🚦 Traffic:
{result.get('traffic')}


🛣 Route:

{route_text}


📏 Distance:
{result.get('distance')} km


⏱ Time:
{result.get('time')} minutes
"""


        self.map_display.insert(
            "end",
            display
        )