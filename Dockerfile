FROM mambaorg/micromamba:latest
USER root

# Activate the base env for all subsequent RUN steps
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Install Python and dependencies (h5py can read AMUSE particle files)
RUN micromamba install -y -n base -c conda-forge \
    openvdb yt numpy h5py \
    python=3.10 pip wheel setuptools \
    && micromamba clean --all --yes

# Set workdir
WORKDIR /workspace

CMD ["/bin/bash"]