import customtkinter as ctk

from ui.control_panel import ControlPanel
from ui.map_panel import MapPanel
from ui.ai_recommendation import AIRecommendation
from ui.result_panel import ResultPanel

from agent.traffic_agent import run_traffic_agent


class Dashboard(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title(
            "Yangon Traffic Agent"
        )

        self.geometry(
            "1400x850"
        )


        # =========================
        # Main Background
        # =========================

        self.grid_rowconfigure(
            0,
            weight=1
        )

        self.grid_rowconfigure(
            1,
            weight=0
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )


        # =========================
        # Main Content
        # =========================

        self.main_frame = ctk.CTkFrame(
            self,
            corner_radius=20
        )

        self.main_frame.grid(
            row=0,
            column=0,
            padx=20,
            pady=20,
            sticky="nsew"
        )


        # Column sizes

        self.main_frame.grid_columnconfigure(
            0,
            weight=1
        )

        self.main_frame.grid_columnconfigure(
            1,
            weight=1.5
        )

        self.main_frame.grid_columnconfigure(
            2,
            weight=1
        )


        self.main_frame.grid_rowconfigure(
            0,
            weight=1
        )


        # =========================
        # Left - Input
        # =========================

        self.control_panel = ControlPanel(
            self.main_frame,
            self.find_route
        )

        self.control_panel.grid(
            row=0,
            column=0,
            padx=10,
            pady=10,
            sticky="nsew"
        )


        # =========================
        # Center - Map
        # =========================

        self.map_panel = MapPanel(
            self.main_frame
        )

        self.map_panel.grid(
            row=0,
            column=1,
            padx=10,
            pady=10,
            sticky="nsew"
        )


        # =========================
        # Right - Result
        # =========================

        self.result_panel = ResultPanel(
            self.main_frame
        )

        self.result_panel.grid(
            row=0,
            column=2,
            padx=10,
            pady=10,
            sticky="nsew"
        )


        # =========================
        # Bottom - AI
        # =========================

        self.ai_panel = AIRecommendation(
            self
        )

        self.ai_panel.grid(
            row=1,
            column=0,
            columnspan=1,
            padx=20,
            pady=(0,15),
            sticky="ew"
        )



    def find_route(self, request):

        """
        Receive request from ControlPanel

        request:
        {
            vehicle,
            start,
            destination
        }
        """

        if "error" in request:

            self.ai_panel.update_text(
                request["error"]
            )

            return


        vehicle = request["vehicle"]
        start = request["start"]
        destination = request["destination"]


        self.ai_panel.update_text(
            "🔍 Finding optimal route..."
        )


        try:

            result = run_traffic_agent(
                start,
                destination,
                vehicle
            )

        except Exception as e:

            self.ai_panel.update_text(
                f"❌ Error: {e}"
            )

            return


        if result.get("error"):

            self.ai_panel.update_text(
                result["error"]
            )

            return


        route = result["route"]
        distance = result["distance"]
        time = result["time"]
        traffic = result.get("traffic", "Unknown")


        # Update Map

        self.map_panel.show_route(
            route
        )


        # Update Route Result

        self.result_panel.update_result(
            route,
            distance,
            time,
            traffic
        )


        # Update AI

        self.ai_panel.update_text(
            result.get(
                "ai_message",
                "No recommendation"
            )
        )



if __name__ == "__main__":

    app = Dashboard()

    app.mainloop()