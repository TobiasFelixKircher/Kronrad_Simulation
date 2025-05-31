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
# Teilkreisradius des Stirnrads
rad_radius = (stirnrad_config["module"] * stirnrad_config["teeth_spur"]) / 2

# Zylinderradius (Außendurchmesser / 2)
zyl_radius = zyl_durchmesser / 2

# Korrektes Wälzverhältnis gemäß Evolvententheorie
wälzverhältnis = rad_radius / zyl_radius

# Positionierung des Stirnrads
position = (
    0,
    -zyl_radius,
    zyl_hoehe * (1 - eingriff_config["tiefe"]) + rad_radius + stirnrad_config["module"]
)

# === Korrektes Abwälzen: Evolventengeometrie ===

# Parameter
delta_theta_stirn_deg = 1
n_steps = int(360 / delta_theta_stirn_deg)
delta_theta_zyl_deg = delta_theta_stirn_deg * wälzverhältnis

# Vorbereitung
bearbeitet = zylinder

for i in range(n_steps):
    # Drehwinkel berechnen
    stirn_winkel = i * delta_theta_stirn_deg
    zyl_winkel = i * delta_theta_zyl_deg

    # Stirnrad: fest im Raum, rotiert nur um eigene Y-Achse
    stirn_i = stirnrad_rohling.rotate((0, 0, 0), (0, 1, 0), stirn_winkel)
    stirn_i = stirn_i.translate(position)

    # Zylinder: rotiert synchron zur Stirnradbewegung um Z-Achse
    zyl_i = bearbeitet.rotate((0, 0, 0), (0, 0, 1), zyl_winkel)

    try:
        bearbeitet = zyl_i.cut(stirn_i)
        print(f"✅ Schritt {i + 1}/{n_steps}: Stirnrad {stirn_winkel:.1f}°, Zylinder {zyl_winkel:.1f}°")
    except Exception as e:
        print(f"⚠️ Fehler in Schritt {i + 1}: {e}")

# Export
cq.exporters.export(bearbeitet, "export/abwaelzen.stl")
print("📦 Export abgeschlossen: export/abwaelzen.stl")