from django.db import models
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

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
    
    def _to_userdatadicts(self, timestamp, prefix, dataitem):
        valid_from_d = dataitem['veljaOd']
        valid_to_d = dataitem['veljaDo']
        infotip = dataitem.get('infotip', '0000')
        podtip = dataitem.get('podtip', '0')
        datadicts = list()
        for extraf in ['clanica_Id', 'kadrovskaSt']:
            val = dataitem.get(extraf, None)
            if val is None:
                continue
            d = { 'field': prefix + '.' + extraf,
                  'value': val,
                  'changed_t': timestamp,
                  'valid_from': valid_from_d,
                  'valid_to': valid_to_d }
            datafields.append(UserDataField)
        for subitem in dataitem.get('data', []):
            subprefix = ".".join(prefix, infotip, podtip)
            valid_from = subitem.get('veljaOd', valid_from_d)
            valid_to = subitem.get('veljaDo', valid_to_d)
            changed_t = subitem.get('datumSpremembe', timestamp)
            for prop, val in subitem.items():
                # Do not add timestamps or seq. number as properties
                if prop in {'veljaOd', 'veljaDo', 'datumSpremembe', "stevilkaSekvence"}:
                    continue
                # Generate property name
                d = { 'field': prefix + '.' + prop,
                      'value': val,
                      'changed_t': changed_t,
                      'valid_from': valid_from_d,
                      'valid_to': valid_to_d }
                datadicts.append(d)
        return datadicts

    def _to_oudata(self, dataset, dataitem):
        ou_data_sets = list()
        valid_from_d = dataitem.get('veljaOd')
        valid_to_d = dataitem.get('veljaDo')
        for subitem in dataitem['data']:
            oud = OUData(
                dataset=dataset,
                name=subitem['organizacijskaEnota'],
                shortname=subitem['organizacijskaEnota_kn'],
                valid_from=subitem.get('veljaOd', valid_from_d),
                valid_to=subitem.get('veljaDo', valid_to_d),
                changed_t=subitem.get('datumSpremembe', dataset.timestamp),
            )
            ou_data_sets.append(oud)
        return ou_data_sets

    def _to_ourelations(self, dataset, dataitem):
        ou_relations = list()
        valid_from_d = dataitem.get('veljaOd')
        valid_to_d = dataitem.get('veljaDo')
        relation = dataitem.get('infotip', '0000') + '.' + \
                   dataitem.get('podtip', '0000')
        uid = dataitem['OE_Id']
        for subitem in dataitem['data']:
            our = OURelation(
                dataset=dataset,
                valid_from=subitem.get('veljaOd', valid_from_d),
                valid_to=subitem.get('veljaDo', valid_to_d),
                relation=relation,
                ou1_id=uid,
                ou2_id=dataitem['id'],
            )
            ou_relations.append(our)
        return ou_relations
    
    def _to_datasets_apis(self):
        in_data = self.parsed_json()
        try:
            timestamp = timezone.datetime.fromisoformat(in_data['TimeStamp'])
        except KeyError:
            timestamp = self.timestamp
        user_dicts = defaultdict(list)
        ds = DataSet(timestamp=timestamp, source=self)
        ds.save()
        ou_data = list()
        ou_relations = list()
        for k, v in in_data.items():
            if type(v) == list:
                for dataitem in v:
                    if k == 'OE':
                        # TODO: fix this
                        ou_data += self._to_oudata(ds, dataitem)
                    elif k == 'NadrejenaOE':
                        # TODO: fix this
                        ou_relations += self._to_ourelations(ds, dataitem)
                    else:
                        uid = dataitem.get('UL_Id', None)
                        if uid is None:
                            continue
                        else:
                            user_dicts[uid] += self._to_userfields(timestamp, k, dataitem)
        user_fields = list()
        # Create UserData and fields from user_dicts
        for uid, fieldlist in user_dicts.items():
            ud = UserData(dataset=ds, uid=uid)
            ud.save()
            for fields in fieldlist:
                uf = UserDataField(userdata=ud, **fields)
                user_fields.append(uf)
        if len(user_fields):
            UserDataField.objects.bulk_create(user_fields)
        # Done filling users.
        OUData.objects.bulk_create(ou_data)
        # TODO: remove the rest of this function
        # create ou relations
        OURelation.objects.bluk_create(ou_relations)

    def _to_datasets_studis(self):
        # TODO implement this
        pass

    def _to_datasets_projekti(self):
        # TODO implement projekti, then this
        pass

    def to_datasets(self):
        handlers = {
            'apis': self._to_datasets_apis,
            'studis': self._to_datasets_studis,
            'projekti': self._to_datasets_projekti,
        }
        return handlers[self.source]()

class DataSet(models.Model):
    def __str__(self):
        return("{}: {}".format(self.timestamp, self.source))
    timestamp = models.DateTimeField()
    source = models.ForeignKey('DataSource', on_delete=models.CASCADE)

class OUData(models.Model):
    def __str__(self):
        return("{}: {} ({})".format(self.shortname, self.name, self.dataset))
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    uid = models.CharField(max_length=64)
    name = models.CharField(max_length=256)
    shortname = models.CharField(max_length=32)

class OURelation(models.Model):
    def __str__(self):
        return("{}: {}-{} ({})".format(self.relation, self.ou1_id, self.ou2_id, self.dataset))
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    relation = models.CharField(max_length=64)
    ou1_id = models.CharField(max_length=32)
    ou2_id = models.CharField(max_length=32)

class UserData(models.Model):
    def __str__(self):
        return("{} ({})".format(self.uid, self.source.id))
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    uid = models.CharField(max_length=64)

class UserDataField(models.Model):
    def __str__(self):
        return("{}: {} ({})".format(self.userdata, self.field, self.data))
    userdata = models.ForeignKey('UserData', on_delete=models.CASCADE, related_name='fields')
    valid_from = models.DateTimeField(null=True)
    valid_to = models.DateTimeField(null=True)
    changed_t = models.DateTimeField(null=True)
    field = models.CharField(max_length=256)
    value = models.CharField(max_length=512)
    

def _datasets_at(timestamp=None, source=None):
    if timestamp is None:
        timestamp = timezone.now()
    dsets = DataSet.objects.filter(
                valid_from__lte=timestamp,
                valid_to__gte=timestamp)
    if source is not None:
        dsets = dsets.filter(source__source=source)
    return dsets.order_by('timestamp')


def userdata_from_datasets(datasets):
    users = defaultdict(dict)
    sources = dict()
    for ds in datasets.prefetch_related('userdata_set'):
        d = {}
        for ud in ds.userdata_set.all():
            d[ud.field] = ud.data
        ulid = d.pop('UL_Id', None)
        if ulid is None:
            continue
        for k in d.keys():
            sources[(ulid, k)] = ds.id
        users[ulid].update(d)
    return users, set(sources.values())

def userdata_at(timestamp=None, source=None):
    datasets = _datasets_at(timestamp, source)
    return userdata_from_datasets(datasets)

def outrees_from_datasets(datasets):
    ous = dict()
    id_relations = defaultdict(dict)
    oud_sources = dict()
    our_sources = dict()
    for ds in datasets.prefetch_related('oudata_set'):
        for oud in ds.oudata_set.all():
            sources[oud.uid] = ds.id
            ous[oud.uid] = (oud.shortname, oud.name)
        for our in ds.ourelation_set.all():
            our_sources[(our.relation, our.ou_id)] = ds.id
            id_relations[our.relation][our.ou1_id] = our.ou2_id
    outree = dict()
    source_ids = set(oud_sources.values()).union(our_sources.values())
    for k, v in id_relations.items():
        toplevel = set() # toplevel OUs
        rel_ous = dict()
        # build a list of OUs with lists for children, add all OUs to toplevel
        for uid, (shortname, name) in ous.items():
            rel_ous[uid] = (uid, shortname, name, [])
            toplevel.add(uid)
        # add missing parents
        for child_id, parent_id in v.items():
            if parent_id not in toplevel:
                toplevel.add(parent_id)
                rel_ous[parent_id] = (parent_id, None, None, [])
        # remove OUs with parents from toplevel, build children lists
        for child_id, parent_id in v.items():
            toplevel.discard(child_id)
            rel_ous[parent_id][3].append(rel_ous[child_id])
        rel_outree = []
        # add toplevel OUs to output
        for i in toplevel:
            rel_outree.append(rel_ous[i])
        outree[k] = rel_outree # tree for relation type k created
    return outree, source_ids
 
def outrees_at(timestamp=None, source=None):
    datasets = _datasets_at(timestamp, source)
    return outrees_from_datasets(datasets)

def ldapactionbatch_at(timestamp=None):
    datasets = _datasets_at(timestamp)
    return ldapactionbatch_from_datasets(datasets)

PRIMARY_OU = [
    "",
]

GROUP_MAPS = [
    "CN=Users,CN={clanica_Id}",
]

GROUP_REGEX_REPLACE = [
    ("CN=Users,CN=2300", "CN=Users,CN=FRI"),
]

PROPERTY_REGEX_REPLACE = [
            
]

def ldapactionbatch_from_datasets(datasets):
    actionbatch = LDAPActionBatch(description=timestamp.isoformat())
    userdata, user_sources = userdata_from_datasets(datasets)
    outrees, ou_sources = outrees_from_datasets(datasets)

    for user, user_props in userdata.items():
        pass
    return actionbatch

class LDAPActionBatch(models.Model):
    description = models.CharField(max_length=512, blank=True, default='')
    actions = models.ManyToManyField('LDAPAction')
    def apply(self):
        pass

class LDAPAction(models.Model):
    ACTION_CHOICES = [
        ('user_upsert', 'Upsert user data'),
        ('add', 'Add'),
        ('delete', 'Delete')]
    sources = models.ManyToManyField('DataSet')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    dn = models.TextField()
    data = models.JSONField()

class LDAPApply(models.Model):
    batch = models.ForeignKey('LDAPActionBatch', on_delete=models.RESTRICT)
    result = models.JSONField()
    timestamp = models.DateTimeField()

