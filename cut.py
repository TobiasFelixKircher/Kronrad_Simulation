import cadquery as cq
from utils.parameter_laden import parameter
from modelle.zylinder import erzeuge_zylinder
from modelle.evolventenrad import InvoluteGear

# Parameter laden
zyl_config = parameter["zylinder"]
stirnrad_config = parameter["stirnrad"]
eingriff_config = parameter["eingriff"]

# Geometrieparameter
zyl_durchmesser = zyl_config["durchmesser"]
zyl_hoehe = zyl_config["hoehe"]
loch_durchmesser = zyl_config["loch_durchmesser"]

# Zylinder erzeugen
zylinder = erzeuge_zylinder(zyl_durchmesser, zyl_hoehe, loch_durchmesser)

# Evolventenrad erzeugen
spur_cfg = {
    "spur_gear_width": stirnrad_config["breite"],
    "y_shift": 0,
    "z_shift": 0
}
gear = InvoluteGear(stirnrad_config)
stirnrad_rohling = gear.get_cq_model(spur_cfg)

# Position berechnen (Mittelpunkt soll in Ursprung starten)
zyl_radius = zyl_durchmesser / 2
rad_radius = (stirnrad_config["module"] * stirnrad_config["teeth_spur"]) / 2

# Positionierung des Stirnrads
position = (
    0,
    -zyl_radius,
    zyl_hoehe * (1 - eingriff_config["tiefe"]) + rad_radius + stirnrad_config["module"]
)

# Anzahl Schritte der Simulation
n_steps = 10
delta_theta_rad = 1  # Schrittweite Drehwinkel Stirnrad [Grad]
wälzverhältnis = rad_radius / zyl_radius

# Startmodell
bearbeitet = zylinder

# Simulationsschritte
for i in range(n_steps):
    winkel_rad = delta_theta_rad * i
    winkel_zyl = delta_theta_rad * wälzverhältnis * i

    stirnrad_rot = stirnrad_rohling.rotate((0, 0, 0), (0, 1, 0), winkel_rad)
    stirnrad_rot = stirnrad_rot.translate(position)
    zylinder_rot = bearbeitet.rotate((0, 0, 0), (0, 0, 1), winkel_zyl)
    bearbeitet = zylinder_rot.cut(stirnrad_rot)
    print(f"Simulationsschritt {i + 1} ausgeführt")

# Exportieren
cq.exporters.export(bearbeitet, "export/abwaelzen.stl")