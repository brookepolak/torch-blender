# input data 
datafilename = 'innMC/turbsph_hdf5_plt_cnt_0173'
starfile = "innMC/stars0173.amuse"
# output name
outfilename = 'innMC/innMC.vdb' 
staroutfile = "innMC/stars0173.csv"

# main vdb grid variable that sets voxel visibility
field = ('flash','dens')

# clipping tolerance for main variable
lower_limit = 1e-20

# extra data fields attached to main data voxels
extra_variables = [('flash','temp')]

# ---------------------------------------------------
# Creating a single frame
# ---------------------------------------------------
from torch_blender import TorchBlender

tb = TorchBlender(datafilename, starfile)

# create the vdb grid
tb.create_vdb(field, log_variable=True, variable_min=lower_limit, 
              extra_variables=extra_variables, outfile=outfilename)

# create the stellar csv file
tb.create_star_csv(mass_cut=10, outfile=staroutfile)

# ---------------------------------------------------
# TODO : Creating many frames for a movie
# ---------------------------------------------------

# max_snap = 100

# for snap in range(max_snap):
    
#     tb = TorchBlender(datafilename, starfile)

#     # create the vdb grid
#     tb.create_vdb(field, log_variable=True, variable_min=lower_limit, 
#                 extra_variables=extra_variables, outfile=outfilename)

#     # create the stellar csv file
#     tb.create_star_csv(mass_cut=10, outfile=staroutfile)
    
#     del tb