import bpy
import random
import csv

def create_star(name, location, size, temp):
    # Create icosphere
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=location)
    star = bpy.context.object
    star.name = name
    
    # Randomize size slightly more
    star.scale = (size, size, size)
    
    # Create material
    mat = bpy.data.materials.new(name=f"StarMat_{name}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    # Create emission node
    node_emission = nodes.new(type='ShaderNodeEmission')
    
    # Set color based on temperature (Kelvin)
    # Simple color mapping: Blue=Hot, White=Mid, Red=Cool
    if temp > 10000:
        color = (0.5, 0.7, 1.0, 1)  # Blue-white
    elif temp > 5000:
        color = (1.0, 1.0, 1.0, 1)  # White
    else:
        color = (1.0, 0.5, 0.2, 1)  # Orange-red
        
    node_emission.inputs[0].default_value = color
    node_emission.inputs[1].default_value = size * 10 # Strength based on size
    
    # Create output node
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    
    # Link nodes
    links = mat.node_tree.links
    links.new(node_emission.outputs[0], node_output.inputs[0])
    
    star.data.materials.append(mat)
    bpy.ops.object.shade_smooth()

# Spawn 100 stars
#for i in range(100):
#    loc = (random.uniform(-50, 50), random.uniform(-50, 50), random.uniform(-50, 50))
#    size = random.uniform(0.1, 1.0)
#    temp = random.uniform(3000, 20000)
#    create_star(f"Star_{i}", loc, size, temp)
CSV_PATH = "/Users/bp4928/Desktop/torch-blender/innMC/stars.csv" 

positions = []
temperatures = []
radii = []
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        x = float(row["x"])
        y = float(row["y"])
        z = float(row["z"])
        T = float(row["T"])
        R = float(row["R"])
        positions.append((x, y, z))
        temperatures.append(T)
        radii.append(R)

for i in range(100):
    loc = positions[i]
    size = radii[i]*0.5
    temp = temperatures[i]
    create_star(f"Star_{i}", loc, size, temp)
