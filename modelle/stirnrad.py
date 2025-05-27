
import cadquery as cq

def erzeuge_stirnrad(modul: float, zaehne: int,durchmesser2: float, breite: float, position=(0, 0, 0)) -> cq.Workplane:
    """
    Erzeugt ein einfaches zylindrisches Stirnrad (nur Volumenkörper ohne Zähne).
    """

    stirnrad = cq.Workplane("XY").circle(durchmesser2 / 2).extrude(breite)
    stirnrad = stirnrad.rotate((0, 0, 0), (1, 0, 0), 90)
    stirnrad = stirnrad.translate(position)
    return stirnrad