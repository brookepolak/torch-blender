import openvdb as vdb
import yt
import numpy as np

class TorchBlender():
    """
    Class for creating a VDB file of Torch simulation data to 
    be loaded into Blender. Optionally also creates a CSV file
    of stars to be loaded into Blender.
    """
    
    def __init__(self, plot_file, part_file=None, norm_box=True, box_size=10.0):
        self.ds = yt.load(plot_file)
        self.part_file = part_file
        self.level = 4 # TODO: get max level
        self.norm_box = norm_box
        self.box_size = box_size
    
    def create_vdb(self, grid_variable=('flash', 'dens'), 
                   log_variable=True, variable_min=None, norm_variable=True,
                   extra_variables=[('flash','temp')],
                   outfile=None):
        
        """
        Creates the VDB file used for rendering in Blender. 
        
        """
        uniform_grid = self.ds.covering_grid(level=self.level, 
                                        left_edge = self.ds.domain_left_edge,
                                        dims=self.ds.domain_dimensions*self.ds.refine_by**self.level)
        
        main_vdb_grid = vdb.FloatGrid()
        
        if log_variable:
            grid_data = np.log10(uniform_grid[grid_variable].v)
            if variable_min != None:
                variable_min - np.log10(variable_min)
        else:
            grid_data = (uniform_grid[grid_variable].v)
            
        # normalize grid data to range (0,1)
        if norm_variable:
            minp = grid_data.min()
            maxp = grid_data.max()
            grid_data = (grid_data - minp)/(maxp-minp)
            if variable_min != None:
                variable_min = (variable_min - minp)/(maxp-minp)
            
        # Setting data to zero makes it invisible in Blender
        if variable_min != None:
            grid_data[grid_data < variable_min] = 0.0

        if self.norm_box:
            voxel_size = self.box_size/float(grid_data.shape[0])
            main_vdb_grid.transform = vdb.createLinearTransform(voxelSize=voxel_size)
        
        main_vdb_grid.name = grid_variable[1]
        main_vdb_grid.background = 0.0
        main_vdb_grid.copyFromArray(grid_data) 
        print(f"Active voxel count: {main_vdb_grid.activeVoxelCount()}")
             
        out_grids = [main_vdb_grid]
        
        # now we can add extra information, i.e. temperature, in the active
        # voxel cells of the main grid variable
        for i,variable in enumerate(extra_variables):
            var_vdb_grid = vdb.FloatGrid()
            var_data = (uniform_grid[variable].v)
            
            if variable_min != None:
                var_data[grid_data < variable_min] = 0.0
            
            if self.norm_box:
                voxel_size = self.box_size/float(var_data.shape[0])
                var_vdb_grid.transform = vdb.createLinearTransform(voxelSize=voxel_size)
                
            var_vdb_grid.name = variable[1]
            var_vdb_grid.background = 0.0
            var_vdb_grid.copyFromArray(var_data) 
            
            out_grids.append(var_vdb_grid)

        # output vdb file
        if outfile is None:
            outfile = f"{grid_variable[1]}.vdb"
            
        vdb.write(outfile, grids=out_grids)
    
    def create_star_csv(self, mass_cut=10.0, radius_scale=0.1, outfile=None):
        """
        Creates a CSV file with stellar data (mass, position, size, 
        temperature) which can be loaded for rendering into Blender.
        
        Only include stars above mass_cut... 
        Be reasonable, or Blender will crash! 

        """
        if self.part_file == None:
            print("WARNING: did not create star csv file, no amuse file specified.")
            return

        from amuse.io import read_set_from_file
        from amuse.units import units
		
        stars = read_set_from_file(self.part_file)
            # only include stars above mass_cut, be reasonable or blender will crash! 
        plot_stars_idx = stars.mass.value_in(units.MSun) >= mass_cut
        stars = stars[plot_stars_idx]

        star_idx = ad['all','particle_csgm'].v == 0.0
        plot_stars_idx = ad['all','particle_mass'][star_idx].to("Msun") >= mass_cut
        
        # Domain edges from yt (same as VDB)
        xmin, ymin, zmin = self.ds.domain_left_edge
        xmax, ymax, zmax = self.ds.domain_right_edge

        xmin = xmin.value
        ymin = ymin.value
        zmin = zmin.value

        xmax = xmax.value
        ymax = ymax.value
        zmax = zmax.value

        # Star positions
        x = stars.x.value_in(stars.x.unit)
        y = stars.y.value_in(stars.y.unit)
        z = stars.z.value_in(stars.z.unit)

        # Normalize 
        x_norm = (x - xmin) / (xmax - xmin) * self.box_size
        y_norm = (y - ymin) / (ymax - ymin) * self.box_size
        z_norm = (z - zmin) / (zmax - zmin) * self.box_size

        positions = np.vstack([x_norm, y_norm, z_norm]).T
        
        T = stars.temperature.value_in(stars.temperature.unit)

        if hasattr(stars, "radius"): 
            # normalize to radius_scale
            minr = stars.radius.min()
            maxr = stars.radius.max()
            R = radius_scale * (stars.radius.value_in(stars.radius.unit) - minr)/(maxr-minr)
        else:
            R = radius_scale * np.ones(len(stars))

        if outfile == None:
            outfile = "stars.csv"

        with open(outfile, "w") as f:
            f.write("x,y,z,T,R\n")
            for i in range(len(stars)):
                f.write(f"{positions[i,0]},{positions[i,1]},{positions[i,2]},{T[i]},{R[i]}\n")

        print(f"Exported normalized stars to {outfile}.")
        
