"""Photoreal mockup stills for match-frame reels, rendered with Blender Cycles.

Every scene is built in code from the brand in src/config/identity.json, the logo SVG,
the textures from `npm run textures` (blender/build/) and CC0 Poly Haven lighting and
materials (`npm run assets`, blender/assets/). Each scene renders an A (dark) and B
(light) variant to public/shots/<scene>_<a|b>.jpg, with the camera aimed so the mark
lands on the match point.

    npm run shots                          # every scene, both variants
    npm run shots -- cards relief          # some scenes
    npm run shots -- cards --variants a --samples 64 --scale 0.5   # quick look
    npm run shots -- --list
"""

import argparse
import json
import math
import pathlib
import re
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
BUILD = HERE / "build"

# Layout of LockupMask.png (keep in sync with src/Textures.tsx)
LOCKUP_MARK_Y = 0.36
LOCKUP_MARK_W = 0.4

IDENT = json.loads((ROOT / "src" / "config" / "identity.json").read_text())
BRAND = IDENT["brand"]
MATCH = IDENT["match"]
SVG = ROOT / "public" / BRAND["logo"]
_vb = re.search(r'viewBox="([^"]+)"', SVG.read_text()).group(1).replace(",", " ").split()
ASPECT = float(_vb[2]) / float(_vb[3])


def lin(hex_):
    """sRGB hex → linear RGBA."""
    h = hex_.lstrip("#")
    c = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


COL = {k: lin(v) for k, v in BRAND["colors"].items()}
SILVER = (0.8, 0.8, 0.8, 1)


# ---------------------------------------------------------------- render setup


def setup(a):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "METAL"
    sc.cycles.device = "GPU"
    sc.cycles.samples = a.samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 12
    sc.cycles.transmission_bounces = 12
    sc.render.resolution_x = 1080
    sc.render.resolution_y = 1920
    sc.render.resolution_percentage = int(a.scale * 100)
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except TypeError:
            pass
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 93
    return sc


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------- node helpers


class Tree:
    def __init__(self, nt):
        self.nt = nt
        nt.nodes.clear()

    def n(self, kind, **kw):
        node = self.nt.nodes.new(kind)
        for k, v in kw.items():
            if k in node.inputs:
                node.inputs[k].default_value = v
            else:
                setattr(node, k, v)
        return node

    def l(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None):
        m = self.n("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.l(v, m.inputs[i])
        return m.outputs[0]

    def mix_rgb(self, blend, fac, a, b):
        m = self.n("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        ins = [s for s in m.inputs if s.type == "RGBA"]
        m.inputs["Factor"].default_value = 1.0
        if isinstance(fac, (int, float)):
            m.inputs["Factor"].default_value = fac
        else:
            self.l(fac, m.inputs["Factor"])
        for sock, v in zip(ins, (a, b)):
            if isinstance(v, tuple):
                sock.default_value = v
            else:
                self.l(v, sock)
        return [s for s in m.outputs if s.type == "RGBA"][0]


def new_material(name):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    t = Tree(m.node_tree)
    out = t.n("ShaderNodeOutputMaterial")
    return m, t, out


def tex_set(t, name, scale, coords):
    """Poly Haven diffuse/rough/normal, box-projected from object coordinates."""
    folder = ASSETS / "tex" / name
    mp = t.n("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    t.l(coords, mp.inputs["Vector"])

    def img(file, data):
        im = bpy.data.images.load(str(folder / file), check_existing=True)
        if data:
            im.colorspace_settings.name = "Non-Color"
        node = t.n("ShaderNodeTexImage", projection="BOX", projection_blend=0.3)
        node.image = im
        t.l(mp.outputs["Vector"], node.inputs["Vector"])
        return node.outputs["Color"]

    nm = t.n("ShaderNodeNormalMap")
    t.l(img("nor.jpg", True), nm.inputs["Color"])
    return img("diff.jpg", False), img("rough.jpg", True), nm.outputs["Normal"]


def decal(t, image, size, center=(0.0, 0.0), axis="+Z"):
    """Factor socket: a square white-on-black mask printed on the object's `axis` face.

    `size` is the mask square's edge in metres, `center` its centre in object
    coordinates of the face plane.
    """
    tc = t.n("ShaderNodeTexCoord")
    sep = t.n("ShaderNodeSeparateXYZ")
    t.l(tc.outputs["Object"], sep.inputs[0])
    nsep = t.n("ShaderNodeSeparateXYZ")
    t.l(tc.outputs["Normal"], nsep.inputs[0])
    x, y, z = sep.outputs
    nx, ny, nz = nsep.outputs
    u, v, facing = {
        "+Z": (x, y, nz),
        "-Y": (x, z, t.math("MULTIPLY", ny, -1)),
        "+Y": (t.math("MULTIPLY", x, -1), z, ny),
        "+X": (y, z, nx),
        "-X": (t.math("MULTIPLY", y, -1), z, t.math("MULTIPLY", nx, -1)),
    }[axis]
    uu = t.math("ADD", t.math("DIVIDE", t.math("SUBTRACT", u, center[0]), size), 0.5)
    vv = t.math("ADD", t.math("DIVIDE", t.math("SUBTRACT", v, center[1]), size), 0.5)
    comb = t.n("ShaderNodeCombineXYZ")
    t.l(uu, comb.inputs[0])
    t.l(vv, comb.inputs[1])
    im = bpy.data.images.load(str(BUILD / image), check_existing=True)
    im.colorspace_settings.name = "Non-Color"
    node = t.n("ShaderNodeTexImage", extension="CLIP", interpolation="Cubic")
    node.image = im
    t.l(comb.outputs[0], node.inputs["Vector"])
    face = t.math("GREATER_THAN", facing, 0.5)
    return t.math("MULTIPLY", node.outputs["Color"], face)


def principled(t, color=(0.8, 0.8, 0.8, 1), rough=0.5, metal=0.0, **kw):
    b = t.n("ShaderNodeBsdfPrincipled")
    for k, v in (("Base Color", color), ("Roughness", rough), ("Metallic", metal), *kw.items()):
        if isinstance(v, (int, float, tuple)):
            b.inputs[k].default_value = v
        else:
            t.l(v, b.inputs[k])
    return b


# ---------------------------------------------------------------- materials


def surface(name, tex, scale=1.0, value=1.0, sat=1.0, tint=None, rough=1.0, normal=1.0):
    """A Poly Haven material, desaturated / darkened / tinted to taste."""
    m, t, out = new_material(name)
    tc = t.n("ShaderNodeTexCoord")
    col, r, n = tex_set(t, tex, scale, tc.outputs["Object"])
    hsv = t.n("ShaderNodeHueSaturation", Saturation=sat, Value=value)
    t.l(col, hsv.inputs["Color"])
    base = hsv.outputs["Color"]
    if tint:
        base = t.mix_rgb("MULTIPLY", 1.0, base, tint)
    b = principled(t, base, t.math("MULTIPLY", r, rough))
    nm_strength = n.node
    nm_strength.inputs["Strength"].default_value = normal
    t.l(n, b.inputs["Normal"])
    t.l(b.outputs[0], out.inputs["Surface"])
    return m


def printed(name, stock, ink, image, size, center=(0.0, 0.0), axis="+Z", stock_rough=0.7, ink_kind="ink", bump=0.0, fibre=True, tex=None, tex_scale=1.0):
    """Card stock / painted panel / cloth with a mask printed on one face.

    ink_kind: 'ink' (flat, slightly glossy), 'foil' (metal), 'blind' (no colour, just the bump).
    tex: a Poly Haven material whose grain is tinted to `stock` (cloth covers, painted plaster).
    """
    m, t, out = new_material(name)
    fac = decal(t, image, size, center, axis)
    nrm = None
    if tex:
        tc = t.n("ShaderNodeTexCoord")
        col, r, n = tex_set(t, tex, tex_scale, tc.outputs["Object"])
        grey = t.n("ShaderNodeHueSaturation", Saturation=0.0, Value=1.6)
        t.l(col, grey.inputs["Color"])
        stock = t.mix_rgb("MULTIPLY", 1.0, grey.outputs["Color"], stock)
        nrm = n
        fibre = False
    if fibre:
        noise = t.n("ShaderNodeTexNoise", Scale=900.0, Detail=6.0)
        bmp = t.n("ShaderNodeBump", Strength=0.08, Distance=0.0002)
        t.l(noise.outputs["Fac"], bmp.inputs["Height"])
        nrm = bmp.outputs["Normal"]
    if bump:
        bmp2 = t.n("ShaderNodeBump", Strength=1.0, Distance=abs(bump), invert=bump < 0)
        t.l(fac, bmp2.inputs["Height"])
        if nrm:
            t.l(nrm, bmp2.inputs["Normal"])
        nrm = bmp2.outputs["Normal"]
    base = principled(t, stock, stock_rough, **{"Sheen Weight": 0.15})
    if ink_kind == "foil":
        top = principled(t, ink, 0.22, 1.0)
    elif ink_kind == "blind":
        # Pressed fibres sit lower, read darker and a touch smoother.
        top = principled(t, t.mix_rgb("MULTIPLY", 1.0, stock, (0.72, 0.72, 0.72, 1)) if not isinstance(stock, tuple) else tuple(c * 0.72 for c in stock[:3]) + (1,), stock_rough * 0.7)
    else:
        top = principled(t, ink, 0.45)
    if nrm:
        t.l(nrm, base.inputs["Normal"])
        t.l(nrm, top.inputs["Normal"])
    mix = t.n("ShaderNodeMixShader")
    t.l(fac, mix.inputs["Fac"])
    t.l(base.outputs[0], mix.inputs[1])
    t.l(top.outputs[0], mix.inputs[2])
    t.l(mix.outputs[0], out.inputs["Surface"])
    return m


def solid(name, color, rough=0.5, metal=0.0, **kw):
    m, t, out = new_material(name)
    b = principled(t, color, rough, metal, **kw)
    t.l(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- geometry


def box(name, dims, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, bevel=0.0, segs=4):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= dims[0]
        v.co.y *= dims[1]
        v.co.z *= dims[2]
    bm.to_mesh(mesh)
    bm.free()
    obj = link(bpy.data.objects.new(name, mesh))
    obj.location = loc
    obj.rotation_euler = Euler([math.radians(r) for r in rot])
    if bevel:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = segs
        mod.harden_normals = True
        for p in mesh.polygons:
            p.use_smooth = True
    if mat:
        mesh.materials.append(mat)
    return obj


def plane(name, size, loc=(0, 0, 0), rot=(0, 0, 0), mat=None):
    w, h = size
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    obj = link(bpy.data.objects.new(name, mesh))
    obj.location = loc
    obj.rotation_euler = Euler([math.radians(r) for r in rot])
    if mat:
        mesh.materials.append(mat)
    return obj


def logo_mesh(name, width, depth, bevel=0.0, mat=None):
    """The SVG as a solid: centred on the origin, front face at z = depth/2, facing +Z."""
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(SVG))
    curves = [o for o in bpy.data.objects if o not in before]
    for c in curves:
        c.data.transform(c.matrix_world)
        c.matrix_world = Matrix.Identity(4)
    pts = [p.co.xy for c in curves for s in c.data.splines for p in (s.bezier_points or s.points)]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    s = width / (max(xs) - min(xs))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    xf = Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, 0))
    meshes = []
    for c in curves:
        c.data.transform(xf)
        c.data.extrude = depth / 2
        c.data.bevel_depth = bevel
        c.data.bevel_resolution = 3
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(c.evaluated_get(dg))
        me.transform(c.matrix_world)
        meshes.append(me)
    for c in curves:
        bpy.data.objects.remove(c)
    bm = bmesh.new()
    for me in meshes:
        bm.from_mesh(me)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = False
    obj = link(bpy.data.objects.new(name, mesh))
    if mat:
        mesh.materials.append(mat)
    return obj


def cylinder(name, radius, depth, loc=(0, 0, 0), rot=(0, 0, 0), mat=None, segs=48):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=radius, radius2=radius, depth=depth)
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = len(p.vertices) == 4
    obj = link(bpy.data.objects.new(name, mesh))
    obj.location = loc
    obj.rotation_euler = Euler([math.radians(r) for r in rot])
    if mat:
        mesh.materials.append(mat)
    return obj


def cyclorama(name, width=12.0, depth=6.0, height=6.0, radius=1.5, mat=None):
    """Seamless studio sweep: floor toward -Y, curving up into a wall at y = 0."""
    prof = [(-depth, 0.0)]
    for i in range(17):
        a = math.radians(90 * i / 16)
        prof.append((-radius + radius * math.sin(a), radius - radius * math.cos(a)))
    prof.append((0.0, height))
    verts, faces = [], []
    for x in (-width / 2, width / 2):
        verts += [(x, y, z) for y, z in prof]
    n = len(prof)
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for p in mesh.polygons:
        p.use_smooth = True
    obj = link(bpy.data.objects.new(name, mesh))
    if mat:
        mesh.materials.append(mat)
    return obj


def uv_plane(name, size, mat=None):
    w, h = size
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new()
    for loop, co in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop.uv = co
    obj = link(bpy.data.objects.new(name, mesh))
    if mat:
        mesh.materials.append(mat)
    return obj


def screen_material(image):
    m, t, out = new_material("screen")
    im = bpy.data.images.load(str(BUILD / image), check_existing=True)
    tx = t.n("ShaderNodeTexImage", interpolation="Cubic")
    tx.image = im
    b = principled(t, (0.0, 0.0, 0.0, 1), 0.04, **{"Emission Strength": 1.3, "Coat Weight": 1.0, "Coat Roughness": 0.03})
    t.l(tx.outputs["Color"], b.inputs["Emission Color"])
    t.l(b.outputs[0], out.inputs["Surface"])
    return m


def etched_glass(name, image, size, center=(0.0, 0.0), axis="-Y"):
    """Clear glass with the mask sand-blasted (frosted) into one face."""
    m, t, out = new_material(name)
    fac = decal(t, image, size, center, axis)
    clear = principled(t, (1, 1, 1, 1), 0.0, **{"Transmission Weight": 1.0, "IOR": 1.5})
    frost = principled(t, (0.95, 0.96, 0.97, 1), 0.45, **{"Transmission Weight": 0.85, "IOR": 1.5})
    mix = t.n("ShaderNodeMixShader")
    t.l(fac, mix.inputs["Fac"])
    t.l(clear.outputs[0], mix.inputs[1])
    t.l(frost.outputs[0], mix.inputs[2])
    t.l(mix.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- world, lights, camera


def world(hdri, strength=1.0, rot=0.0, visible=True, backdrop=(0.05, 0.05, 0.05, 1)):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    if bpy.app.version < (5, 0, 0):
        w.use_nodes = True
    t = Tree(w.node_tree)
    out = t.n("ShaderNodeOutputWorld")
    tc = t.n("ShaderNodeTexCoord")
    mp = t.n("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
    env = t.n("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(ASSETS / "hdri" / f"{hdri}.hdr"), check_existing=True)
    bg = t.n("ShaderNodeBackground", Strength=strength)
    t.l(tc.outputs["Generated"], mp.inputs["Vector"])
    t.l(mp.outputs["Vector"], env.inputs["Vector"])
    t.l(env.outputs["Color"], bg.inputs["Color"])
    if visible:
        t.l(bg.outputs[0], out.inputs["Surface"])
        return
    plain = t.n("ShaderNodeBackground", Color=backdrop, Strength=1.0)
    lp = t.n("ShaderNodeLightPath")
    mix = t.n("ShaderNodeMixShader")
    t.l(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    t.l(bg.outputs[0], mix.inputs[1])
    t.l(plain.outputs[0], mix.inputs[2])
    t.l(mix.outputs[0], out.inputs["Surface"])


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def area(loc, target, size=1.0, power=200.0, color=(1, 1, 1)):
    d = bpy.data.lights.new("area", "AREA")
    d.size = size
    d.energy = power
    d.color = color
    o = link(bpy.data.objects.new("area", d))
    o.location = loc
    aim(o, target)
    return o


def spot(loc, target, power=500.0, angle=40.0, blend=0.4, radius=0.05, color=(1, 1, 1)):
    d = bpy.data.lights.new("spot", "SPOT")
    d.energy = power
    d.spot_size = math.radians(angle)
    d.spot_blend = blend
    d.shadow_soft_size = radius
    d.color = color
    o = link(bpy.data.objects.new("spot", d))
    o.location = loc
    aim(o, target)
    return o


def sun(elevation, azimuth, strength=4.0, angle=0.5):
    d = bpy.data.lights.new("sun", "SUN")
    d.energy = strength
    d.angle = math.radians(angle)
    o = link(bpy.data.objects.new("sun", d))
    el, az = math.radians(elevation), math.radians(azimuth)
    direction = Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    o.location = direction * 10
    aim(o, (0, 0, 0))
    return o


def camera(target, yaw=0.0, pitch=0.0, lens=50.0, fit=None, dist=None, fstop=None, roll=0.0):
    """Look at `target` from yaw (deg around Z, 0 = from -Y) and pitch (deg above).

    `fit` = the mark's width in metres: distance is chosen so it spans match.width of
    the frame (exact head-on, close at modest angles). Lens shift puts the target on
    the match point instead of the frame centre.
    """
    if fit:
        dist = fit / (MATCH["width"] * (9 / 16) * 36 / lens)
    y, p = math.radians(yaw), math.radians(pitch)
    direction = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    d = bpy.data.cameras.new("cam")
    d.lens = lens
    d.sensor_fit = "VERTICAL"
    d.sensor_height = 36
    d.shift_x = -(MATCH["x"] - 0.5) * 9 / 16
    d.shift_y = MATCH["y"] - 0.5
    d.clip_start = 0.005
    o = link(bpy.data.objects.new("cam", d))
    o.location = Vector(target) + direction * dist
    aim(o, target)
    o.rotation_euler.rotate(Euler((0, 0, math.radians(roll))))
    if fstop:
        d.dof.use_dof = True
        d.dof.focus_distance = dist
        d.dof.aperture_fstop = fstop
        d.dof.aperture_blades = 7
    bpy.context.scene.camera = o
    return o


def world_point(obj, local):
    bpy.context.view_layer.update()  # matrix_world is stale until the depsgraph runs
    return obj.matrix_world @ Vector(local)


# ---------------------------------------------------------------- scenes
# Each takes the variant ('a' = dark, 'b' = light) and builds everything.


def scene_cards(v):
    """Business cards on a table: foil on dark stock (A), black ink on white (B)."""
    dark = v == "a"
    world("photo_studio_loft_hall", strength=1.0 if dark else 1.4, rot=120)
    if dark:
        table = surface("table", "concrete_floor_02", scale=4, value=0.42, sat=0.3)
    else:
        table = surface("table", "rough_linen", scale=5, value=0.95, sat=0.35, normal=1.6)
    plane("table", (3, 3), mat=table)
    W, H, T = 0.085, 0.055, 0.0007
    logo_w = 0.032
    stock = COL["ink"] if dark else COL["paper"]
    ink = SILVER if dark else COL["ink"]
    face = printed("card_face", stock, ink, "LogoMask.png", logo_w, ink_kind="foil" if dark else "ink", bump=-0.0003 if dark else 0.0)
    plain = printed("card_plain", stock, ink, "LogoMask.png", 0.0001, ink_kind="ink")
    back = printed("card_back", COL["primary"], COL["onPrimary"], "LockupMask.png", 0.05)
    rot = -16
    for i in range(6):
        box(f"stack{i}", (W, H, T), loc=(0.002 * math.sin(i * 2.1), 0.002 * math.cos(i * 1.7), T / 2 + i * T), rot=(0, 0, rot + 1.5 * math.sin(i)), mat=plain, bevel=0.0002, segs=2)
    top = box("card", (W, H, T), loc=(0, 0, T / 2 + 6 * T), rot=(0, 0, rot), mat=face, bevel=0.0002, segs=2)
    box("back", (W, H, T), loc=(-0.06, 0.07, T / 2), rot=(0, 0, 14), mat=back, bevel=0.0002, segs=2)
    target = world_point(top, (0, 0, T / 2))
    camera(target, yaw=-10, pitch=50, lens=70, fit=logo_w * 1.05, fstop=2.8)


def scene_relief(v):
    """The mark raised out of a plaster wall, raking light from the left."""
    dark = v == "a"
    world("studio_small_09", strength=0.05 if dark else 0.35)
    wall = surface("wall", "grey_plaster" if dark else "white_plaster_02", scale=1.2, value=0.14 if dark else 1.1, sat=0.15, normal=1.5)
    plane("wall", (8, 8), rot=(90, 0, 0), mat=wall)
    width = 0.32
    mark = logo_mesh("mark", width, 0.014, bevel=0.0012, mat=wall)
    mark.rotation_euler = Euler((math.radians(90), 0, 0))
    mark.location = (0, -0.007, 0)
    area((-2.2, -0.7, 0.7), (0, 0, 0), size=0.5, power=110 if dark else 300, color=(1.0, 0.9, 0.78) if dark else (1, 0.97, 0.93))
    camera((0, 0, 0), yaw=8, pitch=4, lens=85, fit=width, fstop=8)


def scene_wallsign(v):
    """Metal letters on stand-offs, gallery wall under a spot: brushed steel on charcoal (A), matte black on white (B)."""
    dark = v == "a"
    world("empty_warehouse_01", strength=0.06 if dark else 1.1, rot=40)
    wall = surface("wall", "grey_plaster" if dark else "white_plaster_02", scale=0.7, value=0.13 if dark else 1.05, sat=0.1)
    plane("wall", (14, 9), loc=(0, 0, 3.0), rot=(90, 0, 0), mat=wall)
    floor = surface("floor", "concrete_floor_02", scale=0.5, value=0.22 if dark else 0.75, sat=0.2, rough=0.55)
    plane("floor", (14, 14), loc=(0, -7, 0), mat=floor)
    width, z = 0.9, 2.1
    if dark:
        letters = solid("steel", (0.85, 0.83, 0.8, 1), rough=0.3, metal=1.0, **{"Anisotropic": 0.6})
    else:
        letters = solid("black", COL["ink"], rough=0.6)
    mark = logo_mesh("mark", width, 0.03, bevel=0.002, mat=letters)
    mark.rotation_euler = Euler((math.radians(90), 0, 0))
    mark.location = (0, -0.06, z)
    spot((0.2, -1.4, z + 2.6), (0, 0, z - 0.2), power=2200 if dark else 900, angle=55, blend=0.7, radius=0.06, color=(1.0, 0.88, 0.74))
    camera((0, -0.075, z), yaw=-14, pitch=-3, lens=50, fit=width, fstop=4)


def scene_totem(v):
    """Free-standing brand totem in an exhibition space."""
    dark = v == "a"
    world("empty_warehouse_01", strength=0.12 if dark else 1.1, rot=200)
    floor = surface("floor", "concrete_floor_02", scale=0.4, value=0.3 if dark else 0.85, sat=0.2, rough=0.5)
    plane("floor", (160, 160), mat=floor)
    W, H, D, base = 0.9, 2.2, 0.1, 0.05
    lock = 0.7
    cz = base + H - 0.22 - lock / 2
    oz = base + H / 2
    panel_col, ink = (COL["primary"], COL["onPrimary"]) if dark else (COL["paper"], COL["ink"])
    mat = printed("panel", panel_col, ink, "LockupMask.png", lock, center=(0, cz - oz), axis="-Y", stock_rough=0.5, fibre=False)
    box("panel", (W, D, H), loc=(0, 0, oz), mat=mat, bevel=0.004)
    box("base", (W * 0.92, 0.45, base), loc=(0, 0, base / 2), mat=solid("base", (0.03, 0.03, 0.03, 1), rough=0.35), bevel=0.003)
    area((-1.8, -2.6, 3.2), (0, 0, 1.4), size=2.5, power=260 if dark else 250)
    mark_z = cz + lock * (0.5 - LOCKUP_MARK_Y)
    camera((0, -D / 2, mark_z), yaw=24, pitch=-5, lens=50, fit=lock * LOCKUP_MARK_W, fstop=2.2)


def scene_billboard(v):
    """Street banner on a pole against an open sky, shot from below."""
    dark = v == "a"
    # A is the same street at a stop or so less exposure: moodier sky, darker frame.
    world("kloofendal_48d_partly_cloudy_puresky", strength=0.4 if dark else 1.1, rot=150)
    W, H, D, z = 2.4, 3.6, 0.08, 7.0
    lock = 1.9
    cz = H / 2 - 0.3 - lock / 2
    panel_col, ink = (COL["primary"], COL["onPrimary"]) if dark else (COL["paper"], COL["ink"])
    mat = printed("banner", panel_col, ink, "LockupMask.png", lock, center=(0, cz), axis="-Y", stock_rough=0.55, fibre=False)
    box("banner", (W, D, H), loc=(0, 0, z), mat=mat, bevel=0.01)
    metal = solid("pole", (0.55, 0.56, 0.58, 1), rough=0.45, metal=1.0)
    cylinder("pole", 0.11, 12.0, loc=(-W / 2 - 0.35, 0.15, 6.0), mat=metal)
    for dz in (H / 2 - 0.2, -H / 2 + 0.2):
        box("arm", (0.5, 0.06, 0.06), loc=(-W / 2 - 0.12, 0.08, z + dz), mat=metal)
    lamp = box("lamp", (0.7, 0.28, 0.12), loc=(-W / 2 - 0.35 + 0.45, 0.15, z + H / 2 + 0.9), rot=(0, -8, 0), mat=solid("lamp", (0.85, 0.85, 0.83, 1), rough=0.35), bevel=0.03)
    box("lamp_arm", (0.5, 0.06, 0.06), loc=(-W / 2 - 0.15, 0.15, z + H / 2 + 0.95), mat=metal)
    mark_z = z + cz + lock * (0.5 - LOCKUP_MARK_Y)
    camera((0, -D / 2, mark_z), yaw=20, pitch=-24, lens=35, fit=lock * LOCKUP_MARK_W, fstop=8)


def scene_boxes(v):
    """Packaging stacked on a seamless studio sweep."""
    dark = v == "a"
    world("studio_small_09", strength=0.7 if dark else 1.1, rot=60, visible=False, backdrop=(0.02, 0.02, 0.02, 1) if dark else (0.8, 0.8, 0.78, 1))
    sweep = solid("sweep", (0.008, 0.008, 0.008, 1) if dark else (0.72, 0.71, 0.68, 1), rough=0.8)
    cyclorama("sweep", mat=sweep)
    S = 0.32
    logo = 0.15
    big_col, big_ink = (COL["primary"], COL["onPrimary"]) if dark else (COL["paper"], COL["ink"])
    big = box("big", (S, S, S), loc=(0, -1.6, S / 2), rot=(0, 0, -22), mat=printed("big", big_col, big_ink, "LogoMask.png", logo, axis="-Y", stock_rough=0.6), bevel=0.003)
    small_col, small_ink = (COL["paper"], COL["ink"]) if dark else (COL["primary"], COL["onPrimary"])
    box("small", (0.2, 0.15, 0.09), loc=(0.02, -1.62, S + 0.045), rot=(0, 0, -8), mat=printed("small", small_col, small_ink, "LogoMask.png", 0.09, axis="+Z", stock_rough=0.6), bevel=0.002)
    box("sleeve", (0.13, 0.13, 0.42), loc=(0.3, -1.4, 0.21), rot=(0, 0, 15), mat=printed("sleeve", COL["accent"], COL["onAccent"], "LogoMask.png", 0.08, center=(0, 0.1), axis="-Y", stock_rough=0.6), bevel=0.002)
    area((-1.6, -3.2, 2.0), (0, -1.6, 0.2), size=1.8, power=200)
    target = world_point(big, (0, -S / 2, 0))
    camera(target, yaw=-22, pitch=8, lens=85, fit=logo, fstop=4)


def scene_phone(v):
    """Phone lying on a table, the brand app on screen."""
    dark = v == "a"
    world("photo_studio_loft_hall", strength=0.9 if dark else 1.3, rot=200)
    if dark:
        table = surface("table", "wood_table_001", scale=2.2, value=0.3, sat=0.7)
    else:
        table = surface("table", "marble_01", scale=1.6, value=1.05, sat=0.2, rough=0.6)
    plane("table", (2, 2), mat=table)
    W, H, T = 0.0716, 0.1476, 0.0079
    rot = -14
    alu = solid("alu", (0.1, 0.1, 0.11, 1) if dark else (0.78, 0.77, 0.75, 1), rough=0.32, metal=1.0)
    box("phone", (W, H, T), loc=(0, 0, T / 2), rot=(0, 0, rot), mat=alu, bevel=0.0045, segs=8)
    sw, sh = W - 0.0045, H - 0.0045
    glass = uv_plane("screen", (sw, sh), mat=screen_material("ScreenA.png" if dark else "ScreenB.png"))
    glass.location = (0, 0, T + 0.00005)
    glass.rotation_euler = Euler((0, 0, math.radians(rot)))
    mark_h = 0.4 * 1179 / ASPECT
    f = (0.4 * 2556 + mark_h / 2) / 2556
    target = world_point(glass, (0, (0.5 - f) * sh, 0))
    camera(target, yaw=-6, pitch=60, lens=85, fit=0.4 * sw, fstop=2.8)


def scene_notebook(v):
    """Cloth-bound notebook: silver foil on brand cloth (A), blind deboss on natural cloth (B)."""
    dark = v == "a"
    world("photo_studio_loft_hall", strength=1.0 if dark else 1.4, rot=80)
    table = surface("table", "concrete_floor_02", scale=2, value=0.4 if dark else 1.0, sat=0.15, normal=0.6)
    plane("table", (2, 2), mat=table)
    W, H, T, board = 0.148, 0.21, 0.016, 0.0025
    logo = 0.05
    cloth = COL["primary"] if dark else COL["paper"]
    cover = printed("cover", cloth, SILVER, "LogoMask.png", logo, center=(0.003, 0.02), ink_kind="foil" if dark else "blind", bump=-0.0006 if dark else -0.0016, tex="rough_linen", tex_scale=9, stock_rough=0.85)
    plain_cloth = printed("cloth", cloth, cloth, "LogoMask.png", 0.0001, tex="rough_linen", tex_scale=9, stock_rough=0.85)
    pages = solid("pages", (0.86, 0.85, 0.82, 1), rough=0.9)
    rot = 18
    group = [
        box("back_board", (W, H, board), loc=(0, 0, board / 2), mat=plain_cloth, bevel=0.0008),
        box("block", (W - 0.006, H - 0.006, T - 2 * board), loc=(0.002, 0, T / 2), mat=pages, bevel=0.0005),
        box("spine", (0.005, H, T), loc=(-W / 2 + 0.0025, 0, T / 2), mat=plain_cloth, bevel=0.0015),
    ]
    front = box("front_board", (W, H, board), loc=(0, 0, T - board / 2), mat=cover, bevel=0.0008)
    for o in group + [front]:
        o.location = Matrix.Rotation(math.radians(rot), 4, "Z") @ Vector(o.location)
        o.rotation_euler = Euler((0, 0, math.radians(rot)))
    target = world_point(front, (0.003, 0.02, board / 2))
    camera(target, yaw=12, pitch=58, lens=70, fit=logo * 1.05, fstop=2.8)


def scene_glass(v):
    """Etched-glass partition: the mark frosted into clear glass, office blurred behind."""
    dark = v == "a"
    world("empty_warehouse_01", strength=0.35 if dark else 1.2, rot=120)
    floor = surface("floor", "concrete_floor_02", scale=0.5, value=0.3 if dark else 0.85, sat=0.2, rough=0.45)
    plane("floor", (160, 160), mat=floor)
    W, H, D = 1.6, 2.6, 0.012
    z = 1.45
    logo = 0.45
    box("glass", (W, D, H), loc=(0, 0, H / 2 + 0.03), mat=etched_glass("glass", "LogoMask.png", logo, center=(0, z - (H / 2 + 0.03))))
    frame = solid("frame", (0.03, 0.03, 0.03, 1), rough=0.4, metal=1.0)
    for x in (-W / 2 - 0.02, W / 2 + 0.02):
        box("post", (0.04, 0.05, H + 0.06), loc=(x, 0, H / 2 + 0.03), mat=frame)
    box("rail", (W + 0.08, 0.05, 0.04), loc=(0, 0, H + 0.06), mat=frame)
    area((1.5, -2.5, 2.8), (0, 0, z), size=2.0, power=200 if dark else 120)
    camera((0, -D / 2, z), yaw=10, pitch=-2, lens=50, fit=logo, fstop=2.0)


SCENES = {
    "relief": scene_relief,
    "cards": scene_cards,
    "wallsign": scene_wallsign,
    "totem": scene_totem,
    "phone": scene_phone,
    "billboard": scene_billboard,
    "boxes": scene_boxes,
    "notebook": scene_notebook,
    "glass": scene_glass,
}


# ---------------------------------------------------------------- main


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="render_shots")
    ap.add_argument("scenes", nargs="*", help="scene names (default: all)")
    ap.add_argument("--variants", default="ab")
    ap.add_argument("--samples", type=int, default=192)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--out", default=str(ROOT / "public" / "shots"))
    ap.add_argument("--save-blend", action="store_true", help="also save each scene as .blend for hand tweaks")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for k, f in SCENES.items():
            print(f"{k:10s} {f.__doc__.splitlines()[0]}")
        return
    missing = [p for p in (BUILD / "LogoMask.png", ASSETS / "hdri") if not p.exists()]
    if missing:
        sys.exit(f"Missing {', '.join(map(str, missing))}: run `npm run textures` and `npm run assets` first")
    names = a.scenes or list(SCENES)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        for v in a.variants:
            sc = setup(a)
            SCENES[name](v)
            sc.render.filepath = str(out / f"{name}_{v}.jpg")
            bpy.ops.render.render(write_still=True)
            if a.save_blend:
                bpy.ops.wm.save_as_mainfile(filepath=str(BUILD / f"{name}_{v}.blend"))
            print(f"rendered {name}_{v}")


main()
