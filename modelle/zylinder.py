import cadquery as cq

def erzeuge_zylinder(durchmesser: float, hoehe: float, loch_durchmesser: float) -> cq.Workplane:
    """
    Erzeugt einen zylindrischen Körper mit einem mittigen Loch.
    Der Mittelpunkt des Zylinders liegt im Ursprung (0, 0, 0).

    Parameter:
        durchmesser (float): Außendurchmesser des Zylinders (in mm)
        hoehe (float): Höhe des Zylinders in Z-Richtung (in mm)
        loch_durchmesser (float): Durchmesser des Lochs in der Mitte

    Rückgabe:
        Workplane-Objekt mit dem gebohrten Zylinder
    """

    # 1. Zylinder im Ursprung erzeugen – Basis liegt in der XY-Ebene (Z=0)
    rohling = cq.Workplane("XY").circle(durchmesser / 2).extrude(hoehe)

    # 2. Mittiges Loch durch den Zylinder bohren – von der Oberseite her
    mit_loch = rohling.faces(">Z").workplane().hole(loch_durchmesser)

    return mit_loch