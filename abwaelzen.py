import os
import tempfile
import time
import cadquery as cq
from vedo import Plotter, Mesh

from utils.parameter_laden import parameter
from modelle.zylinder import erzeuge_zylinder
from modelle.evolventenrad import InvoluteGear

def cq_to_vedo_mesh(cq_solid, color, alpha=1.0):
    """Convert CadQuery solid to vedo Mesh via a temporary STL file."""
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmpfile:
        tmp_filename = tmpfile.name
    cq.exporters.export(cq_solid, tmp_filename)
    mesh = Mesh(tmp_filename, c=color, alpha=alpha)
    os.remove(tmp_filename)
    return mesh

def simulate_abwaelzen_cq(steps, angle_step_deg, gear_ratio, spur_model, crown_model, radius_zylinder, z_shift, visualize=False, plotter=None):
    """
    Simulate the gear shaping process (Abwälzen) of spur gear on crown gear (cylinder) using CadQuery.
    - At each step, the spur gear is rotated and positioned, and the crown gear is rotated accordingly.
    - The positioned spur gear is cut from the rotated crown gear for the current step.
    - Visualization is updated per step to show only the current meshes.
    Args:
        steps (int): Number of simulation steps.
        angle_step_deg (float): Rotation angle per step for spur gear in degrees.
        gear_ratio (float): Gear ratio (pitch radius spur / radius cylinder).
        spur_model (cq.Workplane): CadQuery model of the spur gear (fixed original).
        crown_model (cq.Workplane): CadQuery model of the crown gear / cylinder (fixed original).
        radius_zylinder (float): Radius of the cylinder.
        z_shift (float): Z-axis shift of spur gear to align with cylinder surface.
        visualize (bool): Whether to visualize the intermediate steps.
        plotter (vedo.Plotter): Optional vedo Plotter instance for visualization.
    Returns:
        cq.Workplane: Final shaped crown gear model.
    """
    result = crown_model  # Start from the full cylinder model
    original_crown = crown_model  # Keep reference to original crown to rotate fresh each step

    for i in range(steps):
        angle_spur = i * angle_step_deg
        angle_crown = angle_spur * gear_ratio

        # Rotate spur gear around its own Y-axis and position at cylinder radius + z_shift
        stirn_rot = spur_model.rotate((0, 0, 0), (0, 1, 0), angle_spur)
        stirn_pos = stirn_rot.translate((0, -radius_zylinder, z_shift))

        # Rotate a fresh copy of the crown gear by angle_crown around Z-axis
        crown_rot = original_crown.rotate((0, 0, 0), (0, 0, 1), angle_crown)

        # Cut the rotated spur gear shape from the rotated crown gear
        try:
            result = crown_rot.cut(stirn_pos)
        except Exception as e:
            print(f"Boolean operation failed at step {i}: {e}")
            continue

        # Visualization of current step: clear plotter and show current meshes only
        if visualize and plotter is not None:
            plotter.clear()
            # Show the currently positioned spur gear and the current result mesh only
            vedo_stirn = cq_to_vedo_mesh(stirn_pos.val(), 'red', 0.5)
            vedo_crown = cq_to_vedo_mesh(result.val(), 'lightgray', 1.0)
            plotter.show(vedo_stirn, vedo_crown, resetcam=(i == 0))
            plotter.render()
            time.sleep(0.05)

        print(f"Step {i+1}/{steps}: Spur Gear Angle {angle_spur:.2f}°, Crown Gear Angle {angle_crown:.2f}°")

    return result


if __name__ == "__main__":
    # Load parameters
    zyl_config = parameter["zylinder"]
    stirnrad_config = parameter["stirnrad"]
    eingriff_config = parameter["eingriff"]

    # Geometry parameters
    zyl_durchmesser = zyl_config["durchmesser"]
    zyl_hoehe = zyl_config["hoehe"]
    loch_durchmesser = zyl_config["loch_durchmesser"]

    # Generate initial models
    zylinder = erzeuge_zylinder(zyl_durchmesser, zyl_hoehe, loch_durchmesser)
    spur_cfg = {
        "spur_gear_width": stirnrad_config["breite"],
        "y_shift": 0,
        "z_shift": 0
    }
    gear = InvoluteGear(stirnrad_config)
    stirnrad_rohling = gear.get_cq_model(spur_cfg)

    # Calculate radii
    rad_radius = (stirnrad_config["module"] * stirnrad_config["teeth_spur"]) / 2
    zyl_radius = zyl_durchmesser / 2

    # Calculate gear ratio
    waelzverhaeltnis = rad_radius / zyl_radius

    # Calculate Z-shift for correct engagement depth (Eingriffstiefe)
    z_shift = zyl_hoehe * (1 - eingriff_config["tiefe"]) + rad_radius + stirnrad_config["module"]

    # Simulation parameters
    steps = 360
    angle_step_deg = 1

    # Create vedo plotter instance
    plotter = Plotter(bg='white', size=(800, 600))

    # Run the simulation with visualization
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

    # Export the final shaped crown gear
    cq.exporters.export(result, "export/abwaelzen.stl")
    print("📦 Abwälzsimulation abgeschlossen und exportiert als export/abwaelzen.stl")