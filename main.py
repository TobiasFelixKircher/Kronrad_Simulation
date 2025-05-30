from utils.parameter_laden import parameter
import sys
from pathlib import Path
#nochmal ein Test
# Lokalen Pfad einbinden
projektpfad = Path(__file__).resolve().parent
if str(projektpfad) not in sys.path:
    sys.path.insert(0, str(projektpfad))

# Imports
import cadquery as cq
from modelle.zylinder import erzeuge_zylinder
from modelle.evolventenrad import InvoluteGear


# Parameter
stirnrad_config = parameter["stirnrad"]
stirnrad_breite = stirnrad_config["breite"]

zyl_durchmesser = parameter["zylinder"]["durchmesser"]
zyl_hoehe = parameter["zylinder"]["hoehe"]
loch_durchmesser = parameter["zylinder"]["loch_durchmesser"]

# Modelle erzeugen
zylinder = erzeuge_zylinder(zyl_durchmesser, zyl_hoehe, loch_durchmesser)

# Stirnrad-Position: rechts oben am Zylinderrand (unterster Punkt auf halber Höhe des Zylinders)
stirnrad_durchmesser = stirnrad_config["module"] * stirnrad_config["teeth_spur"]
position = (0, -zyl_durchmesser / 2, zyl_hoehe * (1-parameter["eingriff"]["tiefe"]) + (parameter ["stirnrad"]["module"] * parameter["stirnrad"]["teeth_spur"]) / 2 + parameter["stirnrad"]["module"])

spur_cfg = {
    "spur_gear_width": stirnrad_breite,
    "y_shift": 0,
    "z_shift": 0
}

gear = InvoluteGear(stirnrad_config)
stirnrad = gear.get_cq_model(spur_cfg)
stirnrad = stirnrad.translate(position)

# Kombinieren
modell = zylinder.union(stirnrad)

# Export
export_pfad = projektpfad / "export" / "einfachmodell.stl"
export_pfad.parent.mkdir(parents=True, exist_ok=True)
cq.exporters.export(modell, str(export_pfad))
print(f"✅ Modell exportiert nach: {export_pfad}")