import sys
import os
import json
from typing import Dict, List, TypedDict, Optional
from pathlib import Path


class FilesWithTags(TypedDict, total=False):
    filename: str
    material_tag: str
    tet_mesh: str
    transforms: dict


def cad_to_h5m(
    files_with_tags: FilesWithTags,
    h5m_filename: str = "dagmc.h5m",
    cubit_path: str = "/opt/Coreform-Cubit-2021.5/bin/",
    cubit_filename: Optional[str] = None,
    merge_tolerance: float = 1e-4,
    faceting_tolerance: float = 1.0e-2,
    make_watertight: bool = True,
    imprint: bool = True,
    geometry_details_filename: Optional[str] = None,
    surface_reflectivity_name: str = "reflective",
    exo_filename: Optional[str] = None,
    implicit_complement_material_tag: Optional[str] = None,
    verbose: bool = True,
    graveyard = None
):
    """Converts a CAD files in STP or SAT format into a h5m file for use in
    DAGMC simulations. The h5m file contains material tags associated with the
    CAD files.

    files_with_tags: The file names of the input CAD files with associated
        materials tags in the form of a list of dictionaries where each
        dictionary has a "cad_filename" and "material_tag" key. For example
        [{"material_tag": "mat1", "cad_filename": "part1.stp"}, {"material_tag":
        "mat2", "cad_filename": "part2.stp"}]. If no "material_tag" key is
        provided the material names are derived directly from CAD parts names,
        that can be assigned directly in the CAE.
        There is also an option to createa tet mesh of entries by including a
        "tet_mesh" key in the dictionary.The value is passed to the Cubit mesh
        command. An example entry would be "tet_mesh": "size 0.5".
        A transforms dict can also be included to apply
        transforms to the volumes to be exported. Scal, move and rotation
        are supported. A 'scale' key takes a float as a value and offers the
        option to scale up or down the geometry so that it is in cm units as
        required by most particle transport codes. An example entry would be
        "transforms":{"scale": 10} which would make the geometry 10 times
        bigger. A "move" key takes as its value a either a tuple containing the
        volumes to move (defaults to all ), and a list of three floats
        corresponding to translations in the x, y and z directions respectively.
        An example entry could be "transforms":{"scale": 10,"move":[0,0,10]}
        which makes the geometry 10 times bigger and moves it 10 units in the +z
        direction. Similarly, "transforms":{"scale": 10,"move":([3,7],[0,0,10])}
        would make the geometry 10 times bigger, but only move volumes 3 & 7.
        Additionally, if more than one movement is specified, each volume can
        move separately (as long as number of movements is equal to the number of
        volumes given). For example,
        "transforms":{"scale": 10,"move":([3,7],[[0,0,10],[0,0,-10]])} would
        again make the geometry 10 times bigger, but now would move volume 3
        10 units in the +z direction, and volume 7 10 units in the -z direction.
        10 units in the +z direction. Volume IDs can be found through cubit GUI.
        A "rotation" key takes as its value an iterable of seven floats
        corresponding to a rotation angle, the origin coordinates ax x, y and z,
        and the rotation vector in the x, y and z directions respectively.
        An example entry could be "transforms":{"rotate":[180,0,0,0,0,0,1]},
        which would rotate of 180 deg about the origin in the z-direction.

    h5m_filename: the file name of the output h5m file which is suitable for
        use in DAGMC enabled particle transport codes.
    cubit_filename: the file name of the output cubit file. Should end with .cub
        or .cub5. Includes any tet meshes produced and therefore this output
        can be useful for producing unstructured meshes for use in DAGMC
        simulations.
    cubit_path: the path to the Cubit directory used to import Cubit from. On
        Ubuntu with Cubit 2021.5 this would be "/opt/Coreform-Cubit-2021.5/bin/"
    merge_tolerance: The merge tolerance to apply when merging surfaces into
        one.
    faceting_tolerance: The faceting tolerance to apply when faceting edges. Use
        a faceting_tolerance 1.0e-4
    make_watertight: flag to control if the geometry is made watertight prior to
        exporting the h5m file
    imprint: flag to control if the geometry is imprinted prior to exporting
        the h5m file
    geometry_details_filename: The filename to use when saving the geometry
        details. This include linkages between volume numbers, material tags and
        CAD file names. This can be useful for finding the volume number to
        perform a neutronics tally on.
    surface_reflectivity_name: The DAGMC tag name to associate with reflecting
        surfaces. This changes for some neutronics codes but is "reflective"
        in OpenMC and MCNP.
    implicit_complement_material_tag: Material tag to be assigned to the
        implicit complement. Defaults to vacuum.
    graveyard: Side length of graveyard volume to be generated as a thin, hollow
        cube. Two concentric cubes, one of the provided side length, another
        five units greater than the provided side length, are generated. The
        space between the inner wall of the outer cube and the outer wall of the
        inner cube is defined as the graveyard volume.
    """

    if h5m_filename is None or Path(h5m_filename).suffix == ".h5m":
        pass
    else:
        msg = (
            'The h5m_filename argument should end with ".h5m". The provided '
            f'h5m_filename "{h5m_filename}" does not end with .h5m')
        raise ValueError(msg)

    if exo_filename is None or Path(exo_filename).suffix == ".exo":
        pass
    else:
        msg = (
            'The exo_filename argument should end with ".exo". The provided '
            f'exo_filename "{exo_filename}" does not end with .exo')
        raise ValueError(msg)

    if cubit_filename is None or Path(cubit_filename).suffix in [
            ".cub", ".cub5"]:
        pass
    else:
        msg = (
            'The cubit_filename argument should end with ".cub" or ".cub5". '
            f'The provided cubit_filename "{cubit_filename}" does not end '
            ' with either')
        raise ValueError(msg)

    sys.path.append(cubit_path)

    try:
        import cubit
    except ImportError:
        msg = (
            "import cubit failed, cubit was not importable from the "
            f"provided path {cubit_path}"
        )
        raise ImportError(msg)

    cubit.init([])
    if not verbose:
        cubit.cmd('set echo off')
        cubit.cmd('set info off')
        cubit.cmd('set journal off')
        cubit.cmd('set warning off')

    geometry_details, total_number_of_volumes = find_number_of_volumes_in_each_step_file(
        files_with_tags, cubit, verbose)

    apply_transforms(cubit, geometry_details)

    tag_geometry_with_mats(
        geometry_details, implicit_complement_material_tag, cubit, graveyard
    )

    if imprint and total_number_of_volumes > 1:
        imprint_geometry(cubit)
    if total_number_of_volumes > 1:
        merge_geometry(merge_tolerance, cubit)

    # TODO method requires further testing
    find_reflecting_surfaces_of_reflecting_wedge(
        geometry_details, surface_reflectivity_name, cubit, verbose
    )

    save_output_files(
        make_watertight,
        geometry_details,
        h5m_filename,
        cubit_filename,
        geometry_details_filename,
        faceting_tolerance,
        exo_filename,
        cubit,
        verbose,
    )

    # resets cubit workspace
    cubit.cmd('reset')

    return h5m_filename


def create_tet_mesh(geometry_details, cubit):
    cubit.cmd("Trimesher volume gradation 1.3")

    cubit.cmd("volume all size auto factor 5")
    for entry in geometry_details:
        if "tet_mesh" in entry.keys():
            for volume in entry["volumes"]:
                cubit.cmd(
                    "volume " + str(volume) + " size auto factor 6"
                )  # this number is the size of the mesh 1 is small 10 is large
                cubit.cmd("volume all scheme tetmesh proximity layers off")
                # example entry ' size 0.5'
                cubit.cmd(f"volume {volume} " + entry["tet_mesh"])
                cubit.cmd("mesh volume " + str(volume))


def apply_transforms(cubit, geometry_details):
    for entry in geometry_details:
        if 'transforms' in entry.keys():
            for transform in entry['transforms'].keys():
                if transform == 'move':
                    move_volume(cubit,entry)
                if transform == 'scale':
                    scale_geometry(cubit, entry)
                if transform == 'rotate':
                    rotate_volume(cubit,entry)
    cubit.cmd("healer autoheal vol all")

def scale_geometry(cubit, entry):
    cubit.cmd(
        f'volume {" ".join(entry["volumes"])}  scale  {entry["transforms"]["scale"]}')

def move_volume(cubit, entry):
    if isinstance(entry["transforms"]["move"],tuple):
        if isinstance(entry["transforms"]["move"][1][0],list):
            for vol, mov in enumerate(entry["transforms"]["move"][1]):
                translation = list(map(str,mov))
                cubit.cmd(f'volume {entry["transforms"]["move"][0][vol]}  move  {" ".join(translation)}')
        else:
            vols = list(map(str,entry["transforms"]["move"][0]))
            translation = list(map(str,entry["transforms"]["move"][1]))
            cubit.cmd(f'volume {" ".join(vols)}  move  {" ".join(translation)}')
    else:
        translation = list(map(str,entry["transforms"]["move"]))
        cubit.cmd(f'volume {" ".join(entry["volumes"])}  move  {" ".join(translation)}')

def rotate_volume(cubit, entry):
    rotation_vector = list(map(str,entry["transforms"]["rotate"]))
    rot_angle = rotation_vector[0]
    origin = " ".join(rotation_vector[1:4])
    direction = " ".join(rotation_vector[4:7])
    cubit.cmd(
        f'rotate volume {" ".join(entry["volumes"])}  angle {rot_angle} about origin {origin} direction {direction}')
# TODO implent a flag to allow tet file info to be saved
# def save_tet_details_to_json_file(
#         geometry_details,
#         filename="mesh_details.json"):
#     for entry in geometry_details:
#         material = entry["material"]
#     tets_in_volumes = cubit.parse_cubit_list(
#         "tet", " in volume " + " ".join(entry["volumes"])
#     )
#     print("material ", material, " has ", len(tets_in_volumes), " tets")
#     entry["tet_ids"] = tets_in_volumes
#     with open(filename, "w") as outfile:
#         json.dump(geometry_details, outfile, indent=4)


def save_output_files(
    make_watertight: bool,
    geometry_details: dict,
    h5m_filename: str,
    cubit_filename: str,
    geometry_details_filename: str,
    faceting_tolerance: float,
    exo_filename: str,
    cubit,
    verbose: bool
):
    """This saves the output files"""
    cubit.cmd("set attribute on")
    # use a faceting_tolerance 1.0e-4 or smaller for accurate simulations
    if geometry_details_filename is not None:
        with open(geometry_details_filename, "w") as outfile:
            json.dump(geometry_details, outfile, indent=4)

    Path(h5m_filename).parents[0].mkdir(parents=True, exist_ok=True)
    if verbose:
        print("using faceting_tolerance of ", faceting_tolerance)
    if make_watertight:
        cubit.cmd(
            'export dagmc "'
            + h5m_filename
            + '" faceting_tolerance '
            + str(faceting_tolerance)
            + " make_watertight"
        )
    else:
        cubit.cmd(
            'export dagmc "'
            + h5m_filename
            + '" faceting_tolerance '
            + str(faceting_tolerance)
        )

    create_tet_mesh(geometry_details, cubit)

    if exo_filename is not None:
        Path(exo_filename).parents[0].mkdir(parents=True, exist_ok=True)
        cubit.cmd(f'export mesh "{exo_filename}" overwrite')

    if cubit_filename is not None:
        cubit.cmd('save as "' + cubit_filename + '" overwrite')

    return h5m_filename


def imprint_geometry(cubit):
    cubit.cmd("imprint body all")


def merge_geometry(merge_tolerance: float, cubit):
    """merges the geometry with te specified tolerance

    Args:
        merge_tolerance: The allowable distance between surfaces before merging
            them together. Optional as there is a default built into the DAGMC
            export command
    """
    cubit.cmd(f"merge tolerance {merge_tolerance}")
    cubit.cmd("merge vol all group_results")


def find_all_surfaces_of_reflecting_wedge(new_vols, cubit, verbose: bool):
    surfaces_in_volume = cubit.parse_cubit_list(
        "surface", " in volume " + " ".join(new_vols)
    )
    surface_info_dict = {}
    for surface_id in surfaces_in_volume:
        surface = cubit.surface(surface_id)
        # area = surface.area()
        vertex_in_surface = cubit.parse_cubit_list(
            "vertex", " in surface " + str(surface_id)
        )
        if surface.is_planar() and len(vertex_in_surface) == 4:
            surface_info_dict[surface_id] = {"reflector": True}
        else:
            surface_info_dict[surface_id] = {"reflector": False}
    if verbose:
        print("surface_info_dict", surface_info_dict)
    return surface_info_dict


def find_reflecting_surfaces_of_reflecting_wedge(
    geometry_details, surface_reflectivity_name, cubit, verbose
):
    if verbose:
        print("running find_reflecting_surfaces_of_reflecting_wedge")
    wedge_volume = None
    for entry in geometry_details:
        if verbose:
            print(entry)
            print(entry.keys())
        if "surface_reflectivity" in entry.keys():
            surface_info_dict = entry["surface_reflectivity"]
            wedge_volume = " ".join(entry["volumes"])
            surfaces_in_wedge_volume = cubit.parse_cubit_list(
                "surface", " in volume " + str(wedge_volume)
            )
            if verbose:
                print("found surface_reflectivity")
                print("wedge_volume", wedge_volume)
                print("surfaces_in_wedge_volume", surfaces_in_wedge_volume)
            for surface_id in surface_info_dict.keys():
                if surface_info_dict[surface_id]["reflector"]:
                    if verbose:
                        print(
                            surface_id,
                            "surface originally reflecting but does it still exist",
                        )
                    if surface_id not in surfaces_in_wedge_volume:
                        del surface_info_dict[surface_id]
            for surface_id in surfaces_in_wedge_volume:
                if surface_id not in surface_info_dict.keys():
                    surface_info_dict[surface_id] = {"reflector": True}
                    cubit.cmd(
                        'group "'
                        + surface_reflectivity_name
                        + '" add surf '
                        + str(surface_id)
                    )
                    cubit.cmd("surface " + str(surface_id) + " visibility on")
            entry["surface_reflectivity"] = surface_info_dict
            return geometry_details, wedge_volume
    return geometry_details, wedge_volume


def tag_geometry_with_mats(
    geometry_details, implicit_complement_material_tag, cubit, graveyard
):
    volume_mat_list = []
    for entry in geometry_details:
        if "material_tag" in entry.keys():

            if len(entry['material_tag']) > 27:
                msg = ("material_tag > 28 characters. Material tags "
                       "must be less than 28 characters use in DAGMC. "
                       f"{entry['material_tag']} is too long.")
                raise ValueError(msg)

            cubit.cmd(
                'group "mat:'
                + str(entry["material_tag"])
                + '" add volume '
                + " ".join(entry["volumes"])
            )
            volume_mat_list.append([entry["volumes"],entry["material_tag"]])

            if entry['material_tag'].lower() == 'graveyard':
                if implicit_complement_material_tag is not None:
                    graveyard_volume_number = entry["volumes"][0]
                    cubit.cmd(
                        f'group "mat:{implicit_complement_material_tag}_comp" add vol {graveyard_volume_number}'
                    )
        else:
            print(f'dictionary key material_tag is missing for {entry}')
            print("getting material names directly from name IDs...")
            for vol in entry["volumes"]:
                mat_name = cubit.volume(int(vol)).entity_name().split('@')[0]
                cubit.cmd(
                    'group "mat:'
                    + mat_name
                    + '" add volume '
                    + vol
                )
                volume_mat_list.append([[vol],mat_name])

    if graveyard is not None:
        final_vol_number = int(geometry_details[-1]['volumes'][-1])
        inner = final_vol_number + 1
        outer = final_vol_number + 2
        graveyard_volume_number = final_vol_number + 3
        cubit.cmd("create brick x " + str(graveyard))
        cubit.cmd("create brick x " + str(graveyard+5))
        cubit.cmd("subtract vol "
                + str(inner)
                + "from vol "
                + str(outer)
                )
        cubit.cmd(
            'group "mat:'
            + "Graveyard"
            + '" add volume '
            + str(graveyard_volume_number)
            )

            #check for implicit complement again
        if implicit_complement_material_tag is not None:
            cubit.cmd(
f'group "mat:{implicit_complement_material_tag}_comp" add vol {graveyard_volume_number}'
                )


def find_number_of_volumes_in_each_step_file(files_with_tags, cubit, verbose):
    """ """
    for entry in files_with_tags:
        if verbose:
            print(f'loading {entry["cad_filename"]}')
        current_vols = cubit.parse_cubit_list("volume", "all")
        if entry["cad_filename"].endswith(
                ".stp") or entry["cad_filename"].endswith(".step"):
            import_type = "step"
        elif entry["cad_filename"].endswith(".sat"):
            import_type = "acis"
        else:
            msg = (f'File format for {entry["cad_filename"]} is not supported.'
                   'Try step files or sat files')
            raise ValueError(msg)
        if not Path(entry["cad_filename"]).is_file():
            msg = f'File with filename {entry["cad_filename"]} could not be found'
            raise FileNotFoundError(msg)
        short_file_name = os.path.split(entry["cad_filename"])[-1]
        cubit.cmd(
            "import "
            + import_type
            + ' "'
            + entry["cad_filename"]
            + '" separate_bodies no_surfaces no_curves no_vertices '
        )
        cubit.cmd("healer autoheal vol all")
        all_vols = cubit.parse_cubit_list("volume", "all")
        new_vols = set(current_vols).symmetric_difference(set(all_vols))
        new_vols = list(map(str, new_vols))
        if "material_tag" in entry.keys() and len(new_vols) > 1:
            cubit.cmd(
                "unite vol " +
                " ".join(new_vols) +
                " with vol " +
                " ".join(new_vols))
        all_vols = cubit.parse_cubit_list("volume", "all")
        new_vols_after_unite = set(
            current_vols).symmetric_difference(set(all_vols))
        new_vols_after_unite = list(map(str, new_vols_after_unite))
        entry["volumes"] = new_vols_after_unite
        cubit.cmd(
            'group "' +
            short_file_name +
            '" add volume ' +
            " ".join(
                entry["volumes"]))
        if "surface_reflectivity" in entry.keys():
            entry["surface_reflectivity"] = find_all_surfaces_of_reflecting_wedge(
                new_vols_after_unite, cubit)
            if verbose:
                print(
                    "entry['surface_reflectivity']",
                    entry["surface_reflectivity"])
    cubit.cmd("separate body all")

    # checks the cad is clean and catches some errors with the geometry early
    cubit.cmd("validate vol all")
    # commented out as cmd not known see issue #3
    # cubit.cmd("autoheal analyze vol all")

    return files_with_tags, sum(all_vols)
