import customtkinter as ctk


class ResultPanel(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=15
        )

        self.title = ctk.CTkLabel(
            self,
            text="🛣 Route Result",
            font=("Arial", 22, "bold")
        )

        self.title.pack(
            pady=10
        )


        self.route_label = ctk.CTkLabel(
            self,
            text="Route: -",
            font=("Arial", 16)
        )

        self.route_label.pack(
            pady=5
        )


        self.distance_label = ctk.CTkLabel(
            self,
            text="Distance: -",
            font=("Arial", 16)
        )

        self.distance_label.pack(
            pady=5
        )


        self.time_label = ctk.CTkLabel(
            self,
            text="Estimated Time: -",
            font=("Arial", 16)
        )

        self.time_label.pack(
            pady=5
        )


        self.traffic_label = ctk.CTkLabel(
            self,
            text="Traffic: -",
            font=("Arial", 16)
        )

        self.traffic_label.pack(
            pady=5
        )


    def update_result(
            self,
            route,
            distance,
            time,
            traffic
    ):

        self.route_label.configure(
            text=f"🛣 Route:\n{' → '.join(route)}"
        )

        self.distance_label.configure(
            text=f"📏 Distance: {distance} km"
        )

        self.time_label.configure(
            text=f"⏱ Estimated Time: {time}"
        )

        self.traffic_label.configure(
            text=f"🚦 Traffic: {traffic}"
        )


    def reset(self):

        self.route_label.configure(text="Route: -")
        self.distance_label.configure(text="Distance: -")
        self.time_label.configure(text="Estimated Time: -")
        self.traffic_label.configure(text="Traffic: -")