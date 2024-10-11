import logging

from chap_core.geometry import get_area_polygons
logging.basicConfig(level=logging.INFO)

def test_get_area_polygons():
    feature_collection = get_area_polygons("norway", ["Oslo", "Akershus"])
    assert len(feature_collection.features) == 2
    assert feature_collection.features[0].id == "Oslo"


def test_get_area_polygons_brazil():
    locations = ['ALTA FLORESTA D OESTE',
                 'ARIQUEMES',
                 'CABIXI',
                 'CACOAL',
                 'CEREJEIRAS',
                 'COLORADO DO OESTE',
                 'CORUMBIARA',
                 'COSTA MARQUES',
                 'ESPIGAO D OESTE',
                 'GUAJARA MIRIM',
                 'JARU',
                 'JI PARANA',
                 'MACHADINHO D OESTE',
                 'NOVA BRASILANDIA D OESTE',
                 'OURO PRETO DO OESTE',
                 'PIMENTA BUENO',
                 'PORTO VELHO',
                 'PRESIDENTE MEDICI',
                 'RIO CRESPO',
                 'ROLIM DE MOURA']
    assert len(get_area_polygons("brazil", locations, 2).features)  > 10
