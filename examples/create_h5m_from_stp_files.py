
from cad_to_h5m import cad_to_h5m
import urllib.request
import tarfile

url = 'https://github.com/Shimwell/fusion_example_for_openmc_using_paramak/archive/refs/tags/v0.0.1.tar.gz'
urllib.request.urlretrieve(url, 'v0.0.1.tar.gz')

tar = tarfile.open('v0.0.1.tar.gz', "r:gz")
tar.extractall()
tar.close()

cad_to_h5m(
    files_with_tags=[
        {
            "material_tag": "pf_coil_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/pf_coils.stp",
        },
        {
            "material_tag": "pf_coil_case_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/pf_coil_cases.stp",
        },
        {
            "material_tag": "center_column_shield_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/center_column_shield.stp",
        },
        {
            "material_tag": "firstwall_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/outboard_firstwall.stp",
        },
        {
            "material_tag": "blanket_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/blanket.stp",
        },
        {
            "material_tag": "divertor_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/divertor.stp",
        },
        {
            "material_tag": "supports_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/supports.stp",
        },
        {
            "material_tag": "blanket_rear_wall_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/outboard_rear_blanket_wall.stp",
        },
        {
            "material_tag": "inboard_tf_coils_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/inboard_tf_coils.stp",
        },
        {
            "material_tag": "outer_tf_coil_mat",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/outboard_tf_coil.stp",
        },
        {
            "material_tag": "graveyard",
            "filename": "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/graveyard.stp",
        }
    ],
    h5m_filename=' "fusion_example_for_openmc_using_paramak-0.0.1/stp_files/dagmc.h5m',
    cubit_path='/opt/Coreform-Cubit-2021.5/bin/'
)
