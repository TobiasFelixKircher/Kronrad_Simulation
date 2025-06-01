import os
import tempfile
import time
import cadquery as cq
from vedo import Plotter, Mesh

from utils.parameter_laden import parameter
from modelle.zylinder import erzeuge_zylinder
from modelle.evolventenrad import InvoluteGear

def cq_to_vedo_mesh(cq_solid, color, alpha=1.0):
    """Wandelt ein CadQuery-Solid in einen vedo.Mesh um über eine temporäre STL-Datei."""
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmpfile:
        tmp_filename = tmpfile.name
    cq.exporters.export(cq_solid, tmp_filename)
    mesh = Mesh(tmp_filename, c=color, alpha=alpha)
    os.remove(tmp_filename)
    return mesh

def simulate_abwaelzen_cq(steps, angle_step_deg, gear_ratio, spur_model, crown_model, radius_zylinder, z_shift, visualize=False, plotter=None):
    """
    Simuliert das Abwälzen: Das Stirnrad dreht sich um Y-Achse, der Zylinder um Z-Achse,
    und es wird Material vom Zylinder abgeschnitten.
    """
    result = crown_model           # Aktuelles Kronrad mit schon abgeschnittenem Material
    original_crown = crown_model   # Unverändertes Zylinder-Modell für frische Rotation

    for i in range(steps):
        angle_spur = i * angle_step_deg
        angle_crown = angle_spur * gear_ratio

        # Stirnrad um eigene Y-Achse rotieren
        stirn_rot = spur_model.rotate((0, 0, 0), (0, 1, 0), angle_spur)
        # Stirnrad auf Radius + Z-Verschiebung positionieren
        stirn_pos = stirn_rot.translate((0, -radius_zylinder, z_shift))

        # Kronrad frisch um Z-Achse rotieren
        crown_rot = original_crown.rotate((0, 0, 0), (0, 0, 1), angle_crown)

        # Material abtragen (Boolean Schnitt)
        try:
            result = crown_rot.cut(stirn_pos)
        except Exception as e:
            print(f"Boolean-Operation fehlgeschlagen bei Schritt {i}: {e}")
            continue

        # Visualisierung
        if visualize and plotter is not None:
            plotter.clear()
            vedo_stirn = cq_to_vedo_mesh(stirn_pos.val(), 'red', 0.5)
            vedo_crown = cq_to_vedo_mesh(result.val(), 'lightgray', 1.0)
            plotter.show(vedo_stirn, vedo_crown, resetcam=(i == 0))
            plotter.render()
            time.sleep(0.05)

        print(f"Schritt {i + 1}/{steps}: Stirnrad {angle_spur:.2f}°, Kronenrad {angle_crown:.2f}°")

    return result


if __name__ == "__main__":
    # Parameter laden
    zyl_config = parameter["zylinder"]
    stirnrad_config = parameter["stirnrad"]
    eingriff_config = parameter["eingriff"]

    # Geometrie erzeugen
    zyl_durchmesser = zyl_config["durchmesser"]
    zyl_hoehe = zyl_config["hoehe"]
    loch_durchmesser = zyl_config["loch_durchmesser"]

    zylinder = erzeuge_zylinder(zyl_durchmesser, zyl_hoehe, loch_durchmesser)

    spur_cfg = {
        "spur_gear_width": stirnrad_config["breite"],
        "y_shift": 0,
        "z_shift": 0
    }
    gear = InvoluteGear(stirnrad_config)
    stirnrad_rohling = gear.get_cq_model(spur_cfg)

    # Radien für Wälzverhältnis berechnen
    rad_radius = (stirnrad_config["module"] * stirnrad_config["teeth_spur"]) / 2
    zyl_radius = zyl_durchmesser / 2

    waelzverhaeltnis = rad_radius / zyl_radius

    # Z-Verschiebung Stirnrad (Eingriffstiefe)
    z_shift = zyl_hoehe * (1 - eingriff_config["tiefe"]) + rad_radius + stirnrad_config["module"]

    # Simulationsparameter
    steps = 360
    angle_step_deg = 1

    # vedo-Plotter erzeugen für Visualisierung
    plotter = Plotter(bg='white', size=(800, 600))

    # Simulation starten
    result = simulate_abwaelzen_cq(
        steps=steps,
        angle_step_deg=angle_step_deg,
        gear_ratio=waelzverhaeltnis,
        spur_model=stirnrad_rohling,
        crown_model=zylinder,
        radius_zylinder=zyl_radius,
        z_shift=z_shift,
        visualize=True,
        plotter=plotter
    )

    # Ergebnis exportieren
    export_dir = "export"
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, "abwaelzen.stl")
    cq.exporters.export(result, export_path)
    print(f"📦 Abwälzsimulation abgeschlossen und exportiert als {export_path}")