import openvdb as vdb
import yt
import numpy as np
import h5py

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
                variable_min = np.log10(variable_min)
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

    def _read_amuse_particles(self):
        """Read particle data from AMUSE HDF5 file"""
        with h5py.File(self.part_file, 'r') as f:
            # print("File structure:")
            # f.visit(print)
            # print()
            
            # what we need for blender: 
            # - position (x, y, z)
            # - temperature
            # - size
            
            # Example: Read particle positions and masses
            # Adjust these paths based on your actual file structure
            particles = f['data']['0000000001']['attributes']
            

            x = particles['x'][:]
            y = particles['y'][:]
            z = particles['z'][:]
        
            temp = particles['temperature'][:]   
            lum = particles['luminosity'][:]   
            size = particles['radius'][:]  

            return x,y,z,temp,lum,size
        
        return None
       
    def create_star_vdb(self, radius_scale=0.1, temp_scale=1.0, 
                        spike_length=3.0, spike_intensity=0.7, 
                        num_spikes=4, outfile=None):
        """
        Creates a VDB file with stellar data (position, size, 
        temperature) which can be loaded for rendering into Blender.
        
        Parameters:
        -----------
        radius_scale : float
            Multiplier for star radius to control PSF size
        temp_scale : float  
            Multiplier for temperature to control brightness
        spike_length : float
            Length of diffraction spikes in voxel space (relative to radius)
        spike_intensity : float
            Intensity of diffraction spikes (0-1)
        num_spikes : int
            Number of diffraction spikes (4 or 6)
        outfile : str
            Output filename
        """
        if self.part_file == None:
            print("WARNING: did not create star vdb file, no amuse file specified.")
            return
        
        x, y, z, temp, lum, size = self._read_amuse_particles()
        
        # Create grid matching the gas grid dimensions
        uniform_grid = self.ds.covering_grid(
            level=self.level, 
            left_edge=self.ds.domain_left_edge,
            dims=self.ds.domain_dimensions * self.ds.refine_by**self.level
        )
        
        # Get grid shape and domain info
        grid_shape = uniform_grid[('flash', 'dens')].v.shape
        domain_left = self.ds.domain_left_edge.v
        domain_right = self.ds.domain_right_edge.v
        domain_width = domain_right - domain_left
        
        # Initialize star temperature grid (all zeros = invisible)
        star_temp_grid = np.zeros(grid_shape, dtype=np.float32)
        
        # Normalize temperatures to (0, 1) range for nice visuals
        temp_normalized = (temp - temp.min()) / (temp.max() - temp.min())
        temp_normalized *= temp_scale
        
        print(f"Processing {len(x)} stars...")
        
        # Process each star
        for i in range(len(x)):
            # Convert physical position to voxel indices
            pos = np.array([x[i], y[i], z[i]])
            voxel_pos = ((pos - domain_left) / domain_width * grid_shape).astype(int)
            
            # Check if star is within grid bounds
            if not all(0 <= voxel_pos[j] < grid_shape[j] for j in range(3)):
                continue
            
            # Calculate PSF radius in voxels
            star_radius_physical = size[i] * radius_scale
            star_radius_voxels = int(star_radius_physical / domain_width[0] * grid_shape[0])
            star_radius_voxels = max(star_radius_voxels, 2)  # Minimum 2 voxels
            
            # Create PSF kernel (Gaussian)
            kernel_size = star_radius_voxels * 2 + 1
            sigma = star_radius_voxels / 2.5
            
            # Get temperature for this star
            star_temp = temp_normalized[i]
            
            # Apply 3D Gaussian PSF
            x_range = range(max(0, voxel_pos[0] - star_radius_voxels),
                          min(grid_shape[0], voxel_pos[0] + star_radius_voxels + 1))
            y_range = range(max(0, voxel_pos[1] - star_radius_voxels),
                          min(grid_shape[1], voxel_pos[1] + star_radius_voxels + 1))
            z_range = range(max(0, voxel_pos[2] - star_radius_voxels),
                          min(grid_shape[2], voxel_pos[2] + star_radius_voxels + 1))
            
            for ix in x_range:
                for iy in y_range:
                    for iz in z_range:
                        # Distance from star center
                        dx = ix - voxel_pos[0]
                        dy = iy - voxel_pos[1]
                        dz = iz - voxel_pos[2]
                        dist = np.sqrt(dx**2 + dy**2 + dz**2)
                        
                        # Gaussian PSF
                        psf_value = np.exp(-(dist**2) / (2 * sigma**2))
                        
                        # Add to grid (taking maximum to handle overlapping stars)
                        star_temp_grid[ix, iy, iz] = max(
                            star_temp_grid[ix, iy, iz],
                            star_temp * psf_value
                        )
            
            # Add diffraction spikes
            spike_length_voxels = int(star_radius_voxels * spike_length)
            
            # Create spikes at different angles
            if num_spikes == 4:
                spike_angles = [0, 90, 180, 270]  # 4-pointed star
            elif num_spikes == 6:
                spike_angles = [0, 60, 120, 180, 240, 300]  # 6-pointed star
            else:
                spike_angles = np.linspace(0, 360, num_spikes, endpoint=False)
            
            for angle in spike_angles:
                rad = np.radians(angle)
                
                # Horizontal spike (in XY plane)
                for t in range(1, spike_length_voxels):
                    # Main spike direction
                    spike_x = int(voxel_pos[0] + t * np.cos(rad))
                    spike_y = int(voxel_pos[1] + t * np.sin(rad))
                    spike_z = voxel_pos[2]
                    
                    # Check bounds
                    if not (0 <= spike_x < grid_shape[0] and 
                           0 <= spike_y < grid_shape[1] and
                           0 <= spike_z < grid_shape[2]):
                        break
                    
                    # Spike intensity falls off with distance
                    spike_falloff = np.exp(-t / (spike_length_voxels / 2))
                    spike_value = star_temp * spike_intensity * spike_falloff
                    
                    # Add spike with some width
                    for dz in [-1, 0, 1]:
                        z_idx = spike_z + dz
                        if 0 <= z_idx < grid_shape[2]:
                            width_falloff = 0.5 if dz != 0 else 1.0
                            star_temp_grid[spike_x, spike_y, z_idx] = max(
                                star_temp_grid[spike_x, spike_y, z_idx],
                                spike_value * width_falloff
                            )
        
        # Create VDB grid
        star_vdb_grid = vdb.FloatGrid()
        star_vdb_grid.name = "star_temp"
        star_vdb_grid.background = 0.0
        
        # Apply same transform as gas grid
        if self.norm_box:
            voxel_size = self.box_size / float(grid_shape[0])
            star_vdb_grid.transform = vdb.createLinearTransform(voxelSize=voxel_size)
        
        star_vdb_grid.copyFromArray(star_temp_grid)
        
        print(f"Star grid active voxel count: {star_vdb_grid.activeVoxelCount()}")
        
        # Output VDB file
        if outfile is None:
            outfile = "stars.vdb"
        
        vdb.write(outfile, grids=[star_vdb_grid])
        print(f"Wrote star VDB to {outfile}")
 
