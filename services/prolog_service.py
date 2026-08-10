import os

from pyswip import Prolog


KB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "prolog",
    "knowledge_base.pl"
)


_prolog = None


def _get_engine():

    global _prolog

    if _prolog is None:
        _prolog = Prolog()
        _prolog.consult(KB_PATH)

    return _prolog


def _to_atom(value):
    return str(value).strip().lower().replace(" ", "_")


def _quote(value):
    return "'" + str(value).replace("'", "\\'") + "'"


def get_ai_recommendation(vehicle, traffic, distance, time):

    try:
        prolog = _get_engine()

        query = (
            f"recommend({_to_atom(vehicle)}, {_to_atom(traffic)}, "
            f"{distance}, {_quote(time)}, Recommendation)"
        )

        print("PROLOG QUERY:", query)   # TEMPORARY DEBUG LINE

        results = list(prolog.query(query))

        if results:
            return "🧭 " + str(results[0]["Recommendation"])

        return "No matching rule found. Using standard caution."

    except Exception as e:
        return f"AI reasoning unavailable ({e})."