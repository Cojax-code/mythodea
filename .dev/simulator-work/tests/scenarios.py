import copy

from backend.schema import CATALOG


def scenario(a=None, b=None, seed=12):
    def army(composition):
        return {"blocks": {block: {"unit": composition.get(block, ("archer", 0))[0],
                                    "count": composition.get(block, ("archer", 0))[1]}
                           for block in CATALOG["blocks"]}}
    return {"seed": seed, "armies": {"A": army(a or {"avant": ("archer", 20)}),
                                      "B": army(b or {"avant": ("piquier", 20)})}}


def multi(a=2, b=2, seed=12, frontal=False):
    data = scenario(seed=seed)
    for camp, count in (("A", a), ("B", b)):
        blocks = data["armies"][camp]["blocks"]
        data["armies"][camp] = {"generals": [
            {"position": index + 1, "order": "1-2" if frontal and index == 0 and camp == "A" else "",
             "blocks": copy.deepcopy(blocks)} for index in range(count)]}
    return data
