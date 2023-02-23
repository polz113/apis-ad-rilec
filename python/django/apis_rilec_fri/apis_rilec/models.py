from django.db import models
from django.utils import timezone

from collections import defaultdict


import json

# Create your models here.

class DataSource(models.Model):
    DATA_SOURCES = [('apis', 'Apis'), ('studis', 'Studis')]
    source = models.CharField(max_length=32, choices=DATA_SOURCES)
    timestamp = models.DateTimeField()
    data = models.BinaryField()
    def parsed_json(self):
        return json.loads(self.data)

    def _to_datasets_apis(self):
        in_data = self.parsed_json()
        try:
            timestamp = timezone.datetime.fromisoformat(in_data['TimeStamp'])
        except KeyError:
            timestamp = self.timestamp
        user_data_sets = defaultdict(dict)
        ou_data_sets = defaultdict(lambda: defaultdict(dict))
        ou_parents = defaultdict(dict)
        for k, v in in_data.items():
            if type(v) == list:
                for dataitem in v:
                    valid_from_d = dataitem.get('veljaOd')
                    valid_to_d = dataitem.get('veljaDo')
                    infotip = dataitem.get('infotip', '0000')
                    podtip = dataitem.get('podtip', '0')
                    # try to handle dataitem as user data
                    try:
                        ul_id = dataitem['UL_Id']
                        clanica = dataitem['clanica_Id']
                        kadrovska = dataitem['kadrovskaSt']
                        for subitem in dataitem.get('data', []):
                            d = dict()
                            prefix = "{}.".format(k, infotip, podtip)
                            for prop, val in subitem.items():
                                # Do not add timestamps or seq. number as properties
                                if prop in {'veljaOd', 'veljaDo', 'datumSpremembe', "stevilkaSekvence"}:
                                    continue
                                # Generate property name
                                d[prefix + "." + prop] = val
                            valid_from = subitem.get('veljaOd', valid_from_d)
                            valid_to = subitem.get('veljaDo', valid_to_d)
                            changed_t = subitem.get('datumSpremembe', timestamp)
                            user_data_sets[
                                    (valid_from, valid_to, changed_t, clanica, kadrovska, ul_id)
                                ].update(d)
                    except KeyError:
                        pass
                    # try to handle dataitem as OU data
                    try:
                        oe_id = dataitem['OE_Id']
                        clanica = dataitem['clanica_Id']
                        if k == 'OE':
                            for subitem in dataitem['data']:
                                ou_name = subitem['organizacijskaEnota']
                                ou_shortname = subitem['organizacijskaEnota_kn']
                                valid_from = subitem.get('veljaOd', valid_from_d)
                                valid_to = subitem.get('veljaDo', valid_to_d)
                                changed_t = subitem.get('datumSpremembe', timestamp)
                                d = {'name': ou_name, 'shortname': ou_shortname}
                                ou_data_sets[(valid_from, valid_to, changed_t, clanica)][oe_id].update(d)
                        elif k == 'NadrejenaOE':
                            relation = dataitem.get('infotip', '0000') + '.' + \
                                       dataitem.get('podtip', '0000')
                            for subitem in dataitem['data']:
                                valid_from = subitem.get('veljaOd', valid_from_d)
                                valid_to = subitem.get('veljaDo', valid_to_d)
                                changed_t = subitem.get('datumSpremembe', timestamp)
                                ou_tup = (valid_from, valid_to, changed_t, clanica)
                                ou_parents[ou_tup][oe_id] = (relation, subitem['id'])
                    except KeyError:
                        pass
        # create user datasets
        for k, v in user_data_sets.items():
            valid_from, valid_to, changed_t, clanica, kadrovska, ul_id = k
            v.update({"UL_Id": ul_id, "kadrovskaSt": kadrovska, "clanica_Id": clanica})
            ds = DataSet(timestamp=changed_t, 
                         valid_from=valid_from,
                         valid_to=valid_to,
                         source=self)
            ds.save()
            props = []
            for prop, val in v.items():
                props.append(UserData(dataset=ds, field=prop, data=val))
            if len(props):
                UserData.objects.bulk_create(props)
        # create ou datasets
        for k, v in ou_data_sets.items():
            valid_from, valid_to, changed_t, clanica = k
            ds = DataSet(timestamp=changed_t,
                         valid_from=valid_from,
                         valid_to=valid_to,
                         source=self)
            ds.save()
            oudata_list = []
            for oe_id, vals in v.items():
                oudata_list.append(
                    OUData(dataset=ds,
                           uid = oe_id,
                           name=vals['name'],
                           shortname=v['shortname']))
            OUData.objects.bulk_create(oudata_list)
        # create ou relations
        for k, v in ou_parents.items():
            valid_from, valid_to, changed_t, clanica = k
            ds = DataSet(timestamp=changed_t,
                         valid_from=valid_from,
                         valid_to=valid_to,
                         source=self)
            ds.save()
            relation_list = []
            for oe_id, (relation, ou2_id) in v.items():
                relation_list.append(
                    OURelation(dataset=ds,
                               relation=relation,
                               ou1_id=oe_id,
                               ou2_id=ou2_id,
                    ))
            OURelation.objects.bulk_create(relation_list)


    def _to_datasets_studis(self):
        # TODO implement this
        pass

    def _to_datasets_projekti(self):
        # TODO implement projekti, then this
        pass

    def to_datasets(self):
        handlers = {
            'apis': _to_datasets_apis(self),
            'studis': _to_datasets_studis(self),
            'projekti': _to_datasets_projekti(self),
        }
        return handlers[self.source](self)

class DataSet(models.Model):
    timestamp = models.DateTimeField()
    source = models.ForeignKey('DataSource', on_delete=models.CASCADE)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

class OUData(models.Model):
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    uid = models.CharField(max_length=64)
    name = models.CharField(max_length=256)
    shortname = models.CharField(max_length=32)
    parent_uid = models.CharField(max_length=64, null=True)

class OURelation(models.Model):
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    relation = models.CharField(max_length=64)
    ou1_id = models.CharField(max_length=32)
    ou2_id = models.CharField(max_length=32)

class UserData(models.Model):
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    field = models.CharField(max_length=256)
    data = models.CharField(max_length=512)

class LDAPActionBatch(models.Model):
    description = models.CharField(max_length=512)
    datasets = models.ManyToManyField('DataSet')
    actions = models.ManyToManyField('LDAPAction')
    
def batch_from_apis(timestamp):
    actionbatch = LDAPActionBatch(description=timestamp.isoformat())
    # TODO create actual data for a single user
    oud_dict = dict()
    toplevel_ous = []
    oe_tree = dict()
    user_dict = dict()
    for ds in DataSet.objects.filter(
                valid_from__lte=timestamp,
                valid_to__gte=timestamp
            ).order_by(
                'timestamp'
            ):
        for ud in ds.userdata_set.all():
            pass
        for oud in ds.oudata_set.all():
            pass
        for our in ds.ourelation_set.all():
            pass
        print(ds)
    for k, v in oud_dict.items():
        pass
    for relation, toplevels in toplevel_ous.items():
        for ou in toplevels:
            pass
    return actionbatch

class LDAPAction(models.Model):
    data = models.JSONField()

class LDAPApply(models.Model):
    batch = models.ForeignKey('LDAPActionBatch', on_delete=models.RESTRICT)
    result = models.JSONField()
    timestamp = models.DateTimeField()

