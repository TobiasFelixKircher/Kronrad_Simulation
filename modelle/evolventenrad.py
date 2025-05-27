from math import pi, sin, cos, sqrt, radians
import numpy as np

# Ersatzfunktionen für cart_to_polar, polar_to_cart, rotation_matrix, flip_matrix
def cart_to_polar(point):
    x, y = point
    r = sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    return r, theta

def polar_to_cart(polar):
    r, theta = polar
    return (r * cos(theta), r * sin(theta))

def rotation_matrix(angle):
    return np.array([
        [cos(angle), -sin(angle)],
        [sin(angle),  cos(angle)]
    ])

def flip_matrix(flip_x, flip_y):
    return np.array([
        [-1 if flip_x else 1, 0],
        [0, -1 if flip_y else 1]
    ])
import sys
from svgwrite.path import Path
from svgwrite import mm, Drawing
import ezdxf
import numpy as np
import trimesh
from shapely.geometry import Polygon, LinearRing
import cadquery as cq

class DimensionException(Exception):
    pass


class InvoluteGear:
    def __init__(self, config_section, ring=False, pressure_angle_deg=20,
                 dedendum_factor=1.157, addendum_factor=1.0):
        '''
        Construct an involute gear from config.
        :param config_section: Dictionary for one gear, e.g., config["spur_gear"]
        :param ring: True if this is a ring (internal) gear, otherwise False.
        '''

        # Load parameters from config
        module = config_section["module"]
        teeth = config_section["teeth_spur"]
        fillet = config_section["fillet"]
        backlash = config_section["backlash"]

        gen_args = config_section["gear_gen_args"]
        max_steps = gen_args["max_steps"]
        arc_step_size = gen_args["arc_step_size"]
        reduction_tolerance_deg = gen_args["reduction_tolerance_deg"]

        # Store basic gear properties
        pressure_angle = radians(config_section["pressure_angle"])
        self.reduction_tolerance = radians(reduction_tolerance_deg)
        self.module = module
        self.teeth = teeth
        self.pressure_angle = pressure_angle
        self.max_steps = max_steps
        self.arc_step_size = arc_step_size

        # Tooth geometry
        self.addendum = addendum_factor * module
        self.dedendum = dedendum_factor * module
        if ring:
            self.addendum, self.dedendum = self.dedendum, self.addendum

        # Gear radii
        self.pitch_radius = (module * teeth) / 2
        self.base_radius = cos(pressure_angle) * self.pitch_radius
        self.outer_radius = self.pitch_radius + self.addendum
        self.root_radius = self.pitch_radius - self.dedendum
        self.fillet_radius = fillet if not ring else 0

        # Tooth angles
        self.theta_tooth_and_gap = 2 * pi / teeth
        angular_backlash = backlash / (2 * self.pitch_radius)
        self.theta_tooth = self.theta_tooth_and_gap / 2 + (-angular_backlash if not ring else angular_backlash)

        # Placeholders for further geometric calculations
        self.theta_pitch_intersect = None
        self.theta_full_tooth = None

    '''
    Reduces a line of many points to less points depending on the allowed angle tolerance
    '''
    def reduce_polyline(self, polyline):
        vertices = [[],[]]
        last_vertex = [polyline[0][0], polyline[1][0]]

        # Look through all vertices except start and end vertex
        # Calculate by how much the lines before and after the vertex
        # deviate from a straight path.
        # If the deviation angle exceeds the specification, store it
        for vertex_idx in range(1, len(polyline[0])-1):
            next_slope = np.arctan2(    polyline[1][vertex_idx+1] - polyline[1][vertex_idx+0],
                                        polyline[0][vertex_idx+1] - polyline[0][vertex_idx+0]   )
            prev_slope = np.arctan2(    polyline[1][vertex_idx-0] - last_vertex[1],
                                        polyline[0][vertex_idx-0] - last_vertex[0]   )

            deviation_angle = abs(prev_slope - next_slope)

            if (deviation_angle > self.reduction_tolerance):
                vertices[0] += [polyline[0][vertex_idx]]
                vertices[1] += [polyline[1][vertex_idx]]
                last_vertex = [polyline[0][vertex_idx], polyline[1][vertex_idx]]

        # Return vertices along with first and last point of the original polyline
        return np.array([
            np.concatenate([ [polyline[0][0]], vertices[0], [polyline[0][-1]] ]),
            np.concatenate([ [polyline[1][0]], vertices[1], [polyline[1][-1]] ])
        ])

    def generate_half_tooth(self):
        '''
        Generate half an involute profile, ready to be mirrored in order to create one symmetrical involute tooth
        :return: A numpy array, of the format [[x1, x2, ... , xn], [y1, y2, ... , yn]]
        '''
        # Theta is the angle around the circle, however PHI is simply a parameter for iteratively building the involute
        phis = np.linspace(0, pi, self.max_steps)
        points = []
        reached_limit = False
        self.theta_pitch_intersect = None

        for phi in phis:
            x = (self.base_radius * cos(phi)) + (phi * self.base_radius * sin(phi))
            y = (self.base_radius * sin(phi)) - (phi * self.base_radius * cos(phi))
            point = (x, y)
            dist, theta = cart_to_polar(point)

            if self.theta_pitch_intersect is None and dist >= self.pitch_radius:
                self.theta_pitch_intersect = theta
                self.theta_full_tooth = self.theta_pitch_intersect * 2 + self.theta_tooth
            elif self.theta_pitch_intersect is not None and theta >= self.theta_full_tooth / 2:
                reached_limit = True
                break

            if dist >= self.outer_radius:
                points.append(polar_to_cart((self.outer_radius, theta)))
            elif dist <= self.root_radius:
                points.append(polar_to_cart((self.root_radius, theta)))
            else:
                points.append((x,y))

        if not reached_limit:
            raise Exception("Couldn't complete tooth profile.")

        return np.transpose(points)

    def generate_half_root(self):
        '''
        Generate half of the gap between teeth, for the first tooth
        :return: A numpy array, of the format [[x1, x2, ... , xn], [y1, y2, ... , yn]]
        '''
        root_arc_length = (self.theta_tooth_and_gap - self.theta_full_tooth) * self.root_radius

        points_root = []
        for theta in np.arange(self.theta_full_tooth, self.theta_tooth_and_gap/2 + self.theta_full_tooth/2, self.arc_step_size / self.root_radius):
            # The current circumfrential position we are in the root arc, starting from 0
            arc_position = (theta - self.theta_full_tooth) * self.root_radius
            # If we are in the extemities of the root arc (defined by fillet_radius), then we are in a fillet
            in_fillet = min((root_arc_length - arc_position), arc_position) < self.fillet_radius

            r = self.root_radius

            if in_fillet:
                # Add a circular profile onto the normal root radius to form the fillet.
                # High near the edges, small towards the centre
                # The min() function handles the situation where the fillet size is massive and overlaps itself
                circle_pos = min(arc_position, (root_arc_length - arc_position))
                r = r + (self.fillet_radius - sqrt(pow(self.fillet_radius, 2) - pow(self.fillet_radius - circle_pos, 2)))
            points_root.append(polar_to_cart((r, theta)))

        return np.transpose(points_root)

    def generate_roots(self):
        '''
        Generate both roots on either side of the first tooth
        :return: A numpy array, of the format [ [[x01, x02, ... , x0n], [y01, y02, ... , y0n]], [[x11, x12, ... , x1n], [y11, y12, ... , y1n]] ]
        '''
        self.half_root = self.generate_half_root()
        self.half_root = np.dot(rotation_matrix(-self.theta_full_tooth / 2), self.half_root)
        points_second_half = np.dot(flip_matrix(False, True), self.half_root)
        points_second_half = np.flip(points_second_half, 1)
        self.roots = [points_second_half, self.half_root]

        # Generate a second set of point-reduced root
        self.half_root_reduced = self.reduce_polyline(self.half_root)
        points_second_half = np.dot(flip_matrix(False, True), self.half_root_reduced)
        points_second_half = np.flip(points_second_half, 1)
        self.roots_reduced = [points_second_half, self.half_root_reduced]

        return self.roots_reduced

    def generate_tooth(self):
        '''
        Generate only one involute tooth, without an accompanying tooth gap
        :return: A numpy array, of the format [[x1, x2, ... , xn], [y1, y2, ... , yn]]
        '''
        self.half_tooth = self.generate_half_tooth()
        self.half_tooth = np.dot(rotation_matrix(-self.theta_full_tooth / 2), self.half_tooth)
        points_second_half = np.dot(flip_matrix(False, True), self.half_tooth)
        points_second_half = np.flip(points_second_half, 1)
        self.tooth = np.concatenate((self.half_tooth, points_second_half), axis=1)

        # Generate a second set of point-reduced teeth
        self.half_tooth_reduced = self.reduce_polyline(self.half_tooth)
        points_second_half = np.dot(flip_matrix(False, True), self.half_tooth_reduced)
        points_second_half = np.flip(points_second_half, 1)
        self.tooth_reduced = np.concatenate((self.half_tooth_reduced, points_second_half), axis=1)

        return self.tooth_reduced

    def generate_tooth_and_gap(self):
        '''
        Generate only one tooth and one root profile, ready to be duplicated by rotating around the gear center
        :return: A numpy array, of the format [[x1, x2, ... , xn], [y1, y2, ... , yn]]
        '''

        points_tooth = self.generate_tooth()
        points_roots = self.generate_roots()
        self.tooth_and_gap = np.concatenate((points_roots[0], points_tooth, points_roots[1]), axis=1)
        return self.tooth_and_gap

    def generate_gear(self):
        '''
        Generate the gear profile, and return a sequence of co-ordinates representing the outline of the gear
        :return: A numpy array, of the format [[x1, x2, ... , xn], [y1, y2, ... , yn]]
        '''

        points_tooth_and_gap = self.generate_tooth_and_gap()
        points_teeth = [np.dot(rotation_matrix(self.theta_tooth_and_gap * n), points_tooth_and_gap) for n in range(self.teeth)]
        points_gear = np.concatenate(points_teeth, axis=1)
        return points_gear

    def get_point_list(self):
        '''
        Generate the gear profile, and return a sequence of co-ordinates representing the outline of the gear
        :return: A numpy array, of the format [[x1, y2], [x2, y2], ... , [xn, yn]]
        '''

        gear = self.generate_gear()
        return np.transpose(gear)

    def get_svg(self, unit=mm):
        '''
        Generate an SVG Drawing based of the generated gear profile.
        :param unit: None or a unit within the 'svgwrite' module, such as svgwrite.mm, svgwrite.cm
        :return: An svgwrite.Drawing object populated only with the gear path.
        '''

        points = self.get_point_list()
        width, height = np.ptp(points, axis=0)
        left, top = np.min(points, axis=0)
        size = (width*unit, height*unit) if unit is not None else (width,height)
        dwg = Drawing(size=size, viewBox='{} {} {} {}'.format(left,top,width,height))
        p = Path('M')
        p.push(points)
        p.push('Z')
        dwg.add(p)
        return dwg

    def get_dxf(self):
        points = self.get_point_list()

        doc = ezdxf.new('R2010')
        doc.header['$MEASUREMENT'] = 1
        doc.header['$INSUNITS'] = 4
        msp = doc.modelspace()

        msp.add_lwpolyline(points, dxfattribs = {'closed': True})
        return doc

    # TODO Nitish: Use this to generate cq model of spur gear
    def get_cq_model(self, spur_cfg, swap_yz=True):
        '''
        Erzeugt ein CadQuery-Modell des Zahnrads aus dem 2D-Profil.

        :param spur_cfg: Konfigurationsdictionary mit "spur_gear_width", "y_shift", "z_shift"
        :param swap_yz: Optional: Dreht Modell um X-Achse, damit Y nach oben zeigt
        :return: cq.Workplane-Objekt mit extrudiertem Zahnrad
        '''
        # Parameter
        tooth_width = spur_cfg["spur_gear_width"]
        y_shift = spur_cfg["y_shift"]
        z_shift = spur_cfg["z_shift"]

        # Punkte aus Kontur holen
        points = self.get_point_list()

        # CadQuery braucht 2D-Punkte als Tupel
        wire = cq.Workplane("XY").polyline(points.tolist()).close()
        model = wire.extrude(tooth_width)

        # Ursprungsverschiebung (Zentrum im Ursprung, keine automatische Verschiebung)
        model = model.translate((0, y_shift, z_shift))

        # Optional: Y-Z-Achsen tauschen (Drehung um X)
        if swap_yz:
            model = model.rotate((0, 0, 0), (1, 0, 0), -90)

        return model


    def get_mesh(self, spur_cfg, swap_yz=True):
        '''
        Generate a 3D STL model, with optional axis swap (Z<->Y), and display it with coordinate system.

        :param tooth_width: Width of the gear in mm
        :param swap_yz: If True, rotate gear so Y is "up" instead of Z
        :return: The 3D gear mesh as a trimesh.Trimesh object
        '''
        # Define position parameters
        tooth_width = spur_cfg["spur_gear_width"]
        y_shift = spur_cfg["y_shift"]
        z_shift = spur_cfg["z_shift"]

        # Get and close 2D profile
        points = self.get_point_list()
        if not np.allclose(points[0], points[-1]):
            points = np.vstack([points, points[0]])

        poly = Polygon(LinearRing(points))
        if not poly.is_valid:
            poly = poly.buffer(0)

        # Extrude 2D profile into 3D
        gear_mesh = trimesh.creation.extrude_polygon(poly, height=tooth_width)
        gear_mesh.visual.face_colors = [200, 200, 200, 255]  # Light gray

        # Optional: Rotate gear so Y is "up" (swap Y and Z)
        if swap_yz:
            R = trimesh.transformations.rotation_matrix(
                angle=np.radians(-90),  # clockwise 90° around X
                direction=[1, 0, 0],  # X-axis
                point=[0, 0, 0]
            )
            gear_mesh.apply_transform(R)

        return gear_mesh.apply_translation([0, self.pitch_radius + y_shift, self.root_radius + z_shift])


def error_out(s, *args):
    sys.stderr.write(s + "\n")
