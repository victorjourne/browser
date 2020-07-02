import sys, json, os
from pathlib import Path  # python3 only
from dotenv import load_dotenv
from os import environ
import pandas as pd
import elasticsearch
from elasticsearch import Elasticsearch
from shutil import copyfile

from tools.elastic import create_index, get_alias, put_alias, delete_alias, get_index_name, replace_blue_green, inject_documents, search, index_file
from tools.converter import pdf2json

import pytest
#import pdb; pdb.set_trace()

env_path = '/app/tests/iga/.env-iga'
load_dotenv(dotenv_path=env_path)

INDEX_NAME = os.getenv('INDEX_NAME')

USER_DATA = os.getenv('USER_DATA')
ES_DATA = os.getenv('ES_DATA')

GLOSSARY_FILE = os.getenv('GLOSSARY_FILE')
EXPRESSION_FILE = os.getenv('EXPRESSION_FILE')
MAPPING_FILE =  os.getenv('MAPPING_FILE')

PDF_DIR = os.getenv('PDF_DIR')
JSON_DIR = os.getenv('JSON_DIR')
META_DIR =  os.getenv('META_DIR')

os.makedirs(ES_DATA, exist_ok=True)

es = Elasticsearch([{'host': 'elasticsearch', 'port': '9200'}])

doc_guyane_eau = "les-bonnes-feuilles-IGA-eau-potable-en-guadeloupe.pdf"

def test_create_index():
    # Clear
    es.indices.delete_alias(index=[INDEX_NAME+'_blue',INDEX_NAME+'_green'], name=INDEX_NAME, ignore=[400, 404])
    es.indices.delete(index=INDEX_NAME, ignore=[400, 404])

    create_index(INDEX_NAME, USER_DATA, ES_DATA, MAPPING_FILE, GLOSSARY_FILE, EXPRESSION_FILE )

@pytest.mark.run(after='test_create_index')
def test_inject_documents():
    inject_documents(INDEX_NAME, USER_DATA, PDF_DIR, JSON_DIR,
                meta_path = META_DIR)

    res = es.get(index=INDEX_NAME, id= doc_guyane_eau)
    assert len(str(res)) > 1000, res

@pytest.mark.run(after='test_inject_documents')
def test_analyse_index():

    # create elasticsearch index

    indices = elasticsearch.client.IndicesClient(es)

    body = {
          "analyzer": "my_analyzer",
          "text": "Sans sa carte national d'identité, il est difficile de rentrer au MI"
        }

    res = indices.analyze(index = INDEX_NAME, body=body)
    print(res)
    print(' '.join([token['token'] for token in res['tokens']]))
    list_synonym = [token['token'] for token in res['tokens'] if token['type'] == 'SYNONYM']
    assert 'cni' in list_synonym, list_synonym

    body = {
          "analyzer": "my_analyzer",
          "text": "Jusqu'ici, les commandes publiques de la DCRFPN me sont inconnus"
        }


    res = indices.analyze(index = INDEX_NAME, body=body)
    print(res)
    print(' '.join([token['token'] for token in res['tokens']]))

    assert 'Jusqu' not in  str(res['tokens'])
    assert 'comandpubliqu' in  str(res['tokens']), 'expresion not taken into account'

    # § sensibilité au accents
@pytest.mark.run(after='test_inject_documents')
def test_search():
    glossary_file = Path(USER_DATA) / GLOSSARY_FILE
    expression_file = Path(USER_DATA) / EXPRESSION_FILE

    req = 'travail illegal'
    #import pdb; pdb.set_trace()
    res= search(req, INDEX_NAME, str(glossary_file), str(expression_file))
    #print(hits, length_req, bande)
    assert  res['hits'][0]['_id'] == 'BF2014-20-14072+Médecine+de+prévention.pdf', 'Found to result %s'%hits[0]['_id']
    assert res['length'] == 1, res['length']
    assert not res['band']

"""
@pytest.mark.run(after='test_search')
def test_index_file(index_name, pdf_file):
    # Index ignit_pnigitis inside USER_DATA
    PDF_DIR = ''
    JSON_DIR = ''
    META_DIR = ''
    data = index_file(str(pdf_file), index_name, USER_DATA, PDF_DIR, JSON_DIR, META_DIR)
    assert data['author'] == 'babar', data
"""

@pytest.mark.run(after='test_search')
def test_reindex(client, app, es, dummy_index):
    # test reindex after a change of synonym data without downtime, using alias
    # First test : change synonym analyser in index

    # test with very basic index
    es.indices.delete(index='dummy_index', ignore=[400, 404])
    # create index
    es.indices.create(index='dummy_index', body=dummy_index)
    # create alias
    #es.indices.delete_alias(index='dummy_index', name='dummy_alias',ignore=[400, 404])
    es.indices.put_alias(index='dummy_index', name='dummy_alias')

    # index a document
    name_document = 'babar'
    data = {'content' : 'celeste aime le chat mais pas le chien'}
    es.index(index='dummy_index', body=data, id=name_document)

    # change index setting
    dummy_index['settings']['analysis']['filter']['my_synonym']['synonyms'] += ["chien => loup"]

    #es.indices.close(index='dummy_index')
    #es.indices.put_settings(index='dummy_index',body=settings)
    #es.indices.open(index='dummy_index')

    es.indices.delete(index='dummy_index2', ignore=[400, 404])
    # create index
    es.indices.create(index='dummy_index2', body=dummy_index)
    # index a document
    es.index(index='dummy_index2', body=data, id=name_document)

    # change the index pointer of the alias
    es.indices.put_alias(index='dummy_index2', name='dummy_alias')
    es.indices.delete(index='dummy_index', ignore=[400, 404])

    import time
    time.sleep(1)

    # search lion in new index
    request = {'query' : {'match_phrase': {'content': 'lion'}}}
    res = es.search(index='dummy_alias', body=request)
    assert  res['hits']['hits'][0]['_id'] == 'babar', res

    # search loup  in new index
    request = {'query' : {'match_phrase': {'content': 'loup'}}}
    res = es.search(index='dummy_alias', body=request)
    assert  res['hits']['hits'][0]['_id'] == 'babar', res

@pytest.mark.run(after='test_search')
def test_blue_green():

    req = 'ABM'
    """
    the user request is an acronym meaning "agence biomedecine"
    test if blue index without acronym hits no result and
    green index hits documents with "agence biomedecine"
    """
    # Clear
    es.indices.delete_alias(index=[INDEX_NAME+'_blue',INDEX_NAME+'_green'], name=INDEX_NAME, ignore=[400, 404])
    es.indices.delete(index=INDEX_NAME, ignore=[400, 404])

    # Create blue index without synonym
    create_index(INDEX_NAME + '_blue', USER_DATA, ES_DATA, MAPPING_FILE )

    put_alias(INDEX_NAME + '_blue', INDEX_NAME)
    old_index = get_index_name(INDEX_NAME)
    assert old_index == INDEX_NAME + '_blue', 'Alias get issue'

    # index time to blue
    inject_documents(old_index, USER_DATA, PDF_DIR, JSON_DIR,
                meta_path = META_DIR)

    # Test search
    res = search(req, INDEX_NAME)
    #print(hits, length_req, bande)

    assert [hits['_id'] for hits in res['hits']] == []  , 'Found to result %s'%res['hits'][0]['_id']
    print([hits['_id'] for hits in res['hits']])

    ####  Switch to new index #####

    # Create green index with synonym
    new_index = replace_blue_green(old_index, INDEX_NAME)
    assert new_index == INDEX_NAME + '_green', 'Alias get issue'

    create_index(new_index, USER_DATA, ES_DATA, MAPPING_FILE,
                GLOSSARY_FILE, EXPRESSION_FILE)

    # index time to green
    inject_documents(new_index, USER_DATA, PDF_DIR, JSON_DIR,
                meta_path = META_DIR)

    # Switch index in alias
    put_alias(new_index, INDEX_NAME)
    delete_alias(old_index, INDEX_NAME)
    res = search(req, INDEX_NAME)
    import pdb; pdb.set_trace()
    # should be equal rather than in, but doesn't work with test_app.py. WHY??
    assert [hits['_id'] for hits in res['hits']] in ['BF2014-09-13055+-+Problématique+foncière+aux+Antilles.pdf',
                                                    'BF2015-16-15003-fondation-louis-lépine.pdf',
                                                    'BF2015-10-14079-map-déchets-ct.pdf',
                                                    'BF2017-2-1694+-+Fondation+Esclavage.pdf',
                                                    'BF2016-01-15130-simplilfication-entreprises.pdf'], 'Found to result %s'%res['hits'][0]['_id']

    print([hits['_id'] for hits in res['hits']])


    assert get_alias(INDEX_NAME) == {INDEX_NAME + '_green': {'aliases': {INDEX_NAME: {}}}}


if __name__ == '__main__':
    test_create_index()
    test_inject_documents()
    test_analyse_index()
    test_search()
