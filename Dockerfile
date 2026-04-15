FROM mambaorg/micromamba:latest

USER root

RUN apt-get update && apt-get install -y curl

RUN micromamba install -y -n base -c conda-forge \
    openvdb yt numpy h5py python=3.10 pip wheel setuptools

RUN micromamba clean --all --yes

# Install AMUSE for reading stellar data
#RUN curl -L -O "https://github.com/amusecode/amuse/archive/refs/tags/v2025.9.0.tar.gz" && \
#    tar xzf v2025.9.0.tar.gz && \
#    cd amuse-2025.9.0 && \
#    ./setup && \
#    ./setup install framework

WORKDIR /workspace

CMD ["/bin/bash"]

