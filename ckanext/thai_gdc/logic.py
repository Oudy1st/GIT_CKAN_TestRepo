#!/usr/bin/env python
# encoding: utf-8

import ckan.logic as logic
import ckan.logic.action.update as logic_action_update
import ckan.plugins as plugins
import ckan.model as model
import logging
import ckan.plugins.toolkit as toolkit
import ckan.lib.search as search
from ckanext.thai_gdc.controllers.dataset import DatasetImportController
from ckan.lib.jobs import DEFAULT_QUEUE_NAME

_check_access = logic.check_access
_get_or_bust = logic.get_or_bust

log = logging.getLogger(__name__)

@logic.side_effect_free
def tag_list(context, data_dict):

    model = context['model']

    vocab_id_or_name = data_dict.get('vocabulary_id')
    query = data_dict.get('query') or data_dict.get('q')
    if query:
        query = query.strip()
    all_fields = data_dict.get('all_fields', None)

    _check_access('tag_list', context, data_dict)

    if query:
        tags, count = _tag_search(context, data_dict)
    else:
        #tags = model.Tag.all(vocab_id_or_name)
        tags = None

    if tags:
        if all_fields:
            tag_list = model_dictize.tag_list_dictize(tags, context)
        else:
            tag_list = [tag.name for tag in tags]
    else:
        tag_list = []

    return tag_list

def bulk_update_public(context, data_dict):
    from ckan.lib.search import rebuild

    _check_access('bulk_update_public', context, data_dict)
    for dataset in data_dict['datasets']:
        model.Session.query(model.PackageExtra).filter(model.PackageExtra.package_id == dataset).filter(model.PackageExtra.key == 'allow_harvest').update({"value": "True"})
    model.Session.commit()
    [rebuild(package_id) for package_id in data_dict['datasets']]
    logic_action_update._bulk_update_dataset(context, data_dict, {'private': False})

def dataset_bulk_import(context, data_dict):
    _check_access('package_create', context, data_dict)
    import_uuid = _get_or_bust(data_dict, 'import_uuid')
    queue = DEFAULT_QUEUE_NAME
    dataset_import = DatasetImportController()
    
    toolkit.enqueue_job(dataset_import._record_type_process, [data_dict], title=u'import record package import_id:{}'.format(import_uuid), queue=queue)
                
    toolkit.enqueue_job(dataset_import._stat_type_process, [data_dict], title=u'import stat package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._gis_type_process, [data_dict], title=u'import gis package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._multi_type_process, [data_dict], title=u'import multi package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._other_type_process, [data_dict], title=u'import other package import_id:{}'.format(import_uuid), queue=queue)

    toolkit.enqueue_job(dataset_import._finished_process, [data_dict], title=u'import finished import_id:{}'.format(import_uuid), queue=queue)
    