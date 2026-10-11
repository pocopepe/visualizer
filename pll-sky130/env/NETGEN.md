## netgen

Tim Edwards' netgen (LVS), built from source without sudo. The apt `netgen` is a
different tool (TU-Vienna mesh generator); use the full path below.
Needs tcl8.6-dev and tk8.6-dev (already installed).

    git clone --depth 1 https://github.com/RTimothyEdwards/netgen ~/tools/netgen-src
    cd ~/tools/netgen-src && ./configure --prefix=$HOME/tools/netgen
    make -j8 && make install

Binary: `$HOME/tools/netgen/bin/netgen`

Usage:

    ~/tools/netgen/bin/netgen -batch lvs "a.spice cell" "b.spice cell" \
      /home/pocopepe/pdk/volare/sky130/versions/c6d73a35f524070e85faff4a6a9eef49553ebc2b/sky130B/libs.tech/netgen/sky130B_setup.tcl out.txt

Verified (2026-10-11): two identical one-inverter SPICE netlists with the sky130B
setup file give "Circuits match uniquely."
