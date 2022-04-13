###############################################################################
# Converting step files to h5m file to be read by openmc
###############################################################################
from cad_to_h5m import cad_to_h5m
import numpy as np
import os
import sys

def geom_run(*args):
    dic={}
    for i in args[0]:
        dic[i.split(":")[0]]=i.split(":")[1]
    h5m_filename=dic.get("sim_folder")+".h5m"

    if dic.get("bare_min_geom") is None:
        msg = ("No bare minimum geometry provided")
        raise ValueError(msg)
    geom_list = [i+(".step") for i in dic.get("bare_min_geom").split(",")]

    if dic.get("add_on_geom") is not None:
        geom_list = geom_list + [i+(".step") for i in dic.get("add_on_geom").split(",")]

    #scaling from up to cm & thermal expansion
    if dic.get("scale_thermal")==True:
        scale = float(dic.get("scale_dimension"))*(1.0 + foat(dic.get("expansion_coefficient"))*(float(dic.get("operating_temperature"))-293)) #openmc default units are
    else:
        scale = float(dic.get("scale_dimension"))
    if dic.get("implicit_mat") is not None:
        implicit_mat=dic.get("implicit_mat")
    else:
        implicit_mat=None
    if dic.get("graveyard") is not None:
        graveyard_size=int(dic.get("graveyard"))
    else:
        graveyard_size=None
    if dic.get("bounding_box") is not None:
        bounding_box_percent=int(dic.get("bounding_box"))
    else:
        bounding_box_percent=None

    files_with_tags = [{"cad_filename":"CAD/"+i, "transforms":{'scale':scale},'move':[float(i) for i in dic.get("geom_shift").split(",")]} for i in geom_list]

    cad_to_h5m(h5m_filename= h5m_filename,
            cubit_path="/opt/Coreform-Cubit-2021.5/bin/",
            files_with_tags=files_with_tags,
            faceting_tolerance = float(dic.get("faceting_tolerance")),
            implicit_complement_material_tag = implicit_mat,
            geometry_details_filename = "prova",
            #bounding_box = bounding_box_percent,
            graveyard = graveyard_size)
    return

if __name__ == "__main__":
    geom_run(sys.argv[1:])
