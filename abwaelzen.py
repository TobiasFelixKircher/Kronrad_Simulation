

import math
import cadquery as cq
from utils.parameter_laden import parameter
from modelle.zylinder import erzeuge_zylinder
from modelle.evolventenrad import InvoluteGear

# Parameter laden
zyl_config = parameter["zylinder"]
stirn_config = parameter["stirnrad"]
eingriff = parameter["eingriff"]

zyl_durchmesser = zyl_config["durchmesser"]
zyl_hoehe = zyl_config["hoehe"]
loch_durchmesser = zyl_config["loch_durchmesser"]

stirn_zähne = stirn_config["teeth_spur"]
stirn_modul = stirn_config["module"]
stirn_breite = stirn_config["breite"]

zyl_radius = zyl_durchmesser / 2
stirn_radius = (stirn_modul * stirn_zähne) / 2

# Wälzverhältnis: Zylinder dreht sich langsamer als das Stirnrad
wälzverhältnis = stirn_radius / zyl_radius

# Simulationsparameter
n_steps = 60
delta_theta_deg = 6  # Schrittweite Stirnrad in Grad

# Modelle erzeugen
zylinder = erzeuge_zylinder(zyl_durchmesser, zyl_hoehe, loch_durchmesser)
spur_cfg = {
    "spur_gear_width": stirn_breite,
    "y_shift": 0,
    "z_shift": 0
}
stirnrad_rohling = InvoluteGear(stirn_config)

# Startzustand
bearbeitet = zylinder

# Position Stirnrad über Zylinderrand setzen
eingriffs_tiefe = eingriff["tiefe"]
y_shift = zyl_radius
z_shift = zyl_hoehe * (1 - eingriffs_tiefe) + stirn_radius
position = (0, y_shift, z_shift)

for i in range(n_steps):
    winkel_rad = math.radians(delta_theta_deg * i)
    winkel_zyl = math.radians(delta_theta_deg * wälzverhältnis * i)

    stirnrad_modell = stirnrad_rohling.get_cq_model(spur_cfg)
    stirnrad_rot = stirnrad_modell.rotate((0, 0, 0), (0, 1, 0), math.degrees(winkel_rad))
    stirnrad_rot = stirnrad_rot.translate(position)

    zylinder_rot = bearbeitet.rotate((0, 0, 0), (0, 0, 1), math.degrees(winkel_zyl))
    bearbeitet = zylinder_rot.cut(stirnrad_rot)

    print(f"Simulationsschritt {i+1}/{n_steps} abgeschlossen")

cq.exporters.export(bearbeitet, "export/abwaelzen.stl")
print("📦 Export abgeschlossen: export/abwaelzen.stl")