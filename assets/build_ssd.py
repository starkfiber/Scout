"""Rebuild Scout's decorative M.2 asset with Blender 5.x in background mode.

The rendered board is an illustration. Directory positions and SSD activity are
drawn separately by the UI from measured local data.
"""
import bpy
import math
from mathutils import Vector
from pathlib import Path

out = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def mat(name, color, metallic=0, roughness=.4, glow=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Roughness'].default_value=roughness
    if glow:
        p.inputs['Emission Color'].default_value=(*color,1)
        p.inputs['Emission Strength'].default_value=glow
    return m

pcb=mat('sapphire PCB',(.011,.068,.108),.35,.32)
pcb_edge=mat('board edge',(.021,.14,.19),.35,.31)
chip=mat('ceramic packages',(.022,.036,.06),.19,.3)
chip_face=mat('chip inlay',(.054,.10,.16),.12,.34)
gold=mat('gold contacts',(.72,.45,.15),.75,.22)
cyan=mat('signal traces',(.07,.55,.64),.3,.28,.5)
blue=mat('controller',(.16,.25,.52),.2,.27,.25)
silver=mat('screw ring',(.38,.56,.65),.75,.22)

def cube(name, loc, scale, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object;o.name=name
    o.dimensions=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel:
        b=o.modifiers.new('machined edges','BEVEL');b.width=bevel;b.segments=2
        n=o.modifiers.new('weighted normals','WEIGHTED_NORMAL')
    return o

cube('M.2 2280 board',(0,0,0),(10.3,2.6,.13),pcb,.08)
cube('laminated board edge',(0,0,-.08),(10.15,2.5,.035),pcb_edge,.04)
for x in [-4.5,-3.2,-1.9,-.6,.7,2.0]:
    cube('gold finger', (x,-1.32,.012),(.72,.35,.025),gold,.012)
for x in [3.5,3.9,4.3,4.7]:
    cube('interface contact',(x,1.31,.012),(.22,.24,.025),gold,.006)

# Silkscreen connector guides and readable repeated package rhythm.
for i,x in enumerate([-3.75,-1.55,.65,2.85]):
    base = cube(f'NAND package {i+1}',(x,.08,.27),(1.78,1.75,.31),chip,.08)
    cube(f'NAND face {i+1}',(x,.08,.438),(1.46,1.42,.025),chip_face,.03)
    for u in range(4):
        for v in range(3):
            cube('die light',(x-.49+u*.32,-.34+v*.38,.456),(.17,.13,.006),cyan if (u+v+i)%4==0 else pcb_edge,.009)
    for pin in range(12):
        y=-.65+pin*.132
        cube('package pin',(x-.905,y,.295),(.09,.065,.017),silver,.005)
        cube('package pin',(x+.905,y,.295),(.09,.065,.017),silver,.005)

cube('controller body',(4.25,.02,.30),(1.30,1.68,.38),chip,.07)
cube('controller inlay',(4.25,.02,.497),(1.02,1.40,.025),blue,.025)
for x in [-4.55,-3.75,-2.95,-2.15,-1.35,-.55,.25,1.05,1.85,2.65,3.45]:
    cube('signal line',(x,-1.12,.078),(.07,.12,.007),cyan,.007)
for y in [-.92,-.75,.79,.95]:
    cube('bus trace',(0,y,.079),(8.25,.018,.008),cyan,.008)

bpy.ops.mesh.primitive_torus_add(major_radius=.28,minor_radius=.055,location=(4.55,1.03,.08))
bpy.context.object.name='mounting ring';bpy.context.object.data.materials.append(silver)

# A few floating diagnostic layers make the model feel dissected, while the UI
# keeps actual capacity and folder nodes separate from this illustrative art.
cube('floating data plane',(0,0,1.08),(8.2,1.92,.018),cyan,.015)
for x in [-3.3,-1.1,1.1,3.3]:
    cube('floating glass die',(x,0,1.29),(1.55,1.53,.06),blue,.04)
    cube('floating data core',(x,0,1.34),(1.24,1.20,.016),chip_face,.02)

world=bpy.data.worlds.new('Night lab');bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.015,.03,.06,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.25

def light(name, loc, energy, color, size):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object;o.name=name;o.data.energy=energy;o.data.color=color;o.data.shape='DISK';o.data.size=size
    o.rotation_euler=(Vector((0,0,.15))-o.location).to_track_quat('-Z','Y').to_euler()

light('cyan rim',(1,-4,7),1500,(.17,.78,1.0),6)
light('violet fill',(-4,3,5),1000,(.43,.45,1.0),7)
light('soft top',(3,3,8),900,(.85,.95,1.0),6)
bpy.ops.object.camera_add(location=(7,-10,8))
cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,.42))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=13.8
bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=1600;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(out/'ssd.png')
scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'scout_ssd.blend'))
bpy.ops.render.render(write_still=True)
print('SCOUT_ASSET objects',len(bpy.data.objects),'materials',len(bpy.data.materials),'render',scene.render.filepath)
