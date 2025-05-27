import cadquery as cq
from utils.parameter_laden import parameter
from modelle.zylinder import erzeuge_zylinder
from modelle.evolventenrad import InvoluteGear
import math

# Parameter laden
zyl_config = parameter["zylinder"]
stirnrad_config = parameter["stirnrad"]

eingriff = parameter["eingriff"]["tiefe"]

zyl_durchmesser = parameter["zylinder"]["durchmesser"]
zyl_hoehe = parameter["zylinder"]["hoehe"]
loch_durchmesser = parameter["zylinder"]["loch_durchmesser"]

zylinder = erzeuge_zylinder(zyl_durchmesser, zyl_hoehe, loch_durchmesser)

# Stirnrad-Position: rechts oben am Zylinderrand (unterster Punkt auf halber Höhe des Zylinders)
stirnrad_durchmesser = stirnrad_config["module"] * stirnrad_config["teeth_spur"]
position = (0, -zyl_durchmesser / 2, zyl_hoehe * (1-parameter["eingriff"]["tiefe"]) + (parameter ["stirnrad"]["module"] * parameter["stirnrad"]["teeth_spur"]) / 2 + parameter["stirnrad"]["module"])

# Stirnrad-Geometrie erzeugen
spur_cfg = {
    "spur_gear_width": stirnrad_config["breite"],
    "y_shift": 0,
    "z_shift": 0
}
gear = InvoluteGear(stirnrad_config)
stirnrad_rohling = gear.get_cq_model(spur_cfg)


# Simulationsparameter
steps = 10
winkel_pro_step = 360 / steps
r_zyl = zyl_durchmesser / 2
r_stirn = (stirnrad_config["module"] * stirnrad_config["teeth_spur"]) / 2
winkelverhältnis = r_zyl / r_stirn

# Ausgangsmodell
bearbeitet = zylinder

for i in range(steps):
    print("Simulationsschritt " + str(i) +" ausgeführt")
    winkel_zyl = math.radians(i * winkel_pro_step)
    winkel_stirn = math.radians(i * winkel_pro_step * winkelverhältnis)

    # Position berechnen
    x = 0
    y = math.sin(winkel_zyl) * r_zyl
    z = math.cos(winkel_zyl) * r_zyl + zyl_hoehe * (1 - eingriff)

    # Stirnrad kopieren, drehen und positionieren
    stirnrad = stirnrad_rohling.rotate((0, -zyl_durchmesser / 2, zyl_hoehe * (1 - parameter["eingriff"]["tiefe"]) + (parameter["stirnrad"]["module"] * parameter["stirnrad"]["teeth_spur"]) / 2 + parameter["stirnrad"]["module"]), (0, 1, 0), 15)
    stirnrad = stirnrad.translate((x, y, z))

    # Zylinder abtragen
    bearbeitet = bearbeitet.cut(stirnrad)

# Exportieren
cq.exporters.export(bearbeitet, "export/abwaelzung_simuliert.stl")