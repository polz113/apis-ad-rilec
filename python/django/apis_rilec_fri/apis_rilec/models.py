from django.db import models
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

from collections import defaultdict
import json
import string
import os


# Create your models here.

FIELD_DELIMITER='__'


def get_rules():
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, 'translation_rules.json')) as f:
        d = json.load(f)
    return d['TRANSLATIONS'], d['USER_RULES'], d['GROUP_RULES']


class DataSource(models.Model):
    DATA_SOURCES = [('apis', 'Apis'), ('studis', 'Studis')]
    source = models.CharField(max_length=32, choices=DATA_SOURCES)
    timestamp = models.DateTimeField()
    data = models.BinaryField()
    
    def parsed_json(self):
        return json.loads(self.data)
    
    def userdata(self, timestamp=None):
        pass

    def grouptrees(self, timestamp=None):
        pass

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
            d = { 'field': FIELD_DELIMITER.join([prefix, extraf]),
                  'value': val,
                  'changed_t': timestamp,
                  'valid_from': valid_from_d,
                  'valid_to': valid_to_d }
            # print(d)
            datadicts.append(d)
        for fieldgroup, subitem in enumerate(dataitem.get('data', [])):
            subprefix = FIELD_DELIMITER.join([prefix, infotip, podtip])
            valid_from = subitem.get('veljaOd', valid_from_d)
            valid_to = subitem.get('veljaDo', valid_to_d)
            changed_t = subitem.get('datumSpremembe', timestamp)
            for prop, val in subitem.items():
                # Do not add timestamps or seq. number as properties
                if prop in {'veljaOd', 'veljaDo', 'datumSpremembe', "stevilkaSekvence"}:
                    continue
                # Generate property name
                d = { 'field': FIELD_DELIMITER.join([subprefix, prop]),
                      'value': val,
                      'changed_t': changed_t,
                      'fieldgroup': fieldgroup,
                      'valid_from': valid_from,
                      'valid_to': valid_to }
                datadicts.append(d)
        return datadicts

    def _to_oudata(self, dataset, dataitem):
        ou_data_sets = list()
        valid_from_d = dataitem.get('veljaOd')
        valid_to_d = dataitem.get('veljaDo')
        uid=dataitem['OE_Id']
        for subitem in dataitem['data']:
            oud = OUData(
                dataset=dataset,
                uid=uid,
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
        relation = FIELD_DELIMITER.join([dataitem.get('infotip', '0000'),
                                         dataitem.get('podtip', '0000')])
        uid = dataitem['OE_Id']
        for subitem in dataitem['data']:
            our = OURelation(
                dataset=dataset,
                valid_from=subitem.get('veljaOd', valid_from_d),
                valid_to=subitem.get('veljaDo', valid_to_d),
                relation=relation,
                ou1_id=uid,
                ou2_id=subitem['id'],
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
                        ou_data += self._to_oudata(ds, dataitem)
                    elif k == 'NadrejenaOE':
                        ou_relations += self._to_ourelations(ds, dataitem)
                    else:
                        uid = dataitem.get('UL_Id', None)
                        if uid is None:
                            continue
                        else:
                            user_dicts[uid] += self._to_userdatadicts(timestamp, k, dataitem)
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
        # Done filling users. Handle OUs
        OUData.objects.bulk_create(ou_data)
        OURelation.objects.bulk_create(ou_relations)

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
    changed_t = models.DateTimeField(null=True)
    uid = models.CharField(max_length=64)
    name = models.CharField(max_length=256)
    shortname = models.CharField(max_length=32)


class OURelation(models.Model):
    def __str__(self):
        return("{}: {}-{} ({})".format(self.relation, self.ou1_id, self.ou2_id, self.dataset))
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    changed_t = models.DateTimeField(null=True)
    relation = models.CharField(max_length=64)
    ou1_id = models.CharField(max_length=32)
    ou2_id = models.CharField(max_length=32)


class UserData(models.Model):
    def __str__(self):
        return("{} ({})".format(self.uid, self.dataset))
    dataset = models.ForeignKey('DataSet', on_delete=models.CASCADE)
    uid = models.CharField(max_length=64)

    def as_dicts(self, timestamp=None):
        if timestamp is None:
            timestamp = timezone.now()
        dicts = list()
        d = None
        prev_fieldgroup = None
        ffields = self.fields.filter(
                    valid_from__lte=timestamp,
                    valid_to__gte=timestamp
                ).order_by(
                    'fieldgroup'
                )
        common_d = {"uid": self.uid}
        for i in ffields.filter(fieldgroup=None):
            common_d[i.field] = i.value
        for i in ffields.exclude(fieldgroup=None):
            if i.fieldgroup is None or i.fieldgroup != prev_fieldgroup:
                if d is not None:
                    dicts.append(d)
                prev_fieldgroup = i.fieldgroup
                d = common_d.copy()
            d[i.field] = i.value
        if d is not None:
            dicts.append(d)
        return dicts

    def as_translated(self, translation_rules, timestamp=None):
        translated_dicts = list()
        for datadict in self.as_dicts(timestamp=timestamp):
            for fieldname, (template, ruledict) in translation_rules.items():
                t = string.Template(template)
                default = ruledict.get("", "")
                try:
                    key = t.substitute(datadict)
                    data_template = ruledict.get(key, default)
                    t2 = string.Template(data_template)
                    d = t2.substitute(datadict)
                    datadict[fieldname] = d
                except KeyError as e:
                    pass
            translated_dicts.append(datadict)
        return translated_dicts

class UserDataField(models.Model):
    def __str__(self):
        return("{}: {} ({})".format(self.userdata, self.field, self.value))
    userdata = models.ForeignKey('UserData', on_delete=models.CASCADE, related_name='fields')
    valid_from = models.DateTimeField(null=True)
    valid_to = models.DateTimeField(null=True)
    changed_t = models.DateTimeField(null=True)
    fieldgroup = models.IntegerField(null=True)
    field = models.CharField(max_length=256)
    value = models.CharField(max_length=512)


def outrees_at(timestamp=None, source=None):
    if timestamp is None:
        timestamp = timezone.now()
    ouds = OUData.objects.filter(valid_to__gte=timestamp,
                                 valid_from__lte=timestamp)
    ours = OURelation.objects.filter(valid_to__gte=timestamp,
                                 valid_from__lte=timestamp)
    if source is not None:
        ouds = ouds.filter(dataset__source=source)
        ours = ouds.filter(dataset__source=source)
    ous = dict()
    id_relations = defaultdict(dict)
    oud_sources = dict()
    our_sources = dict()
    for oud in ouds:
        source_id = oud.dataset.source_id
        oud_sources[oud.uid] = source_id
        ous[oud.uid] = (oud.shortname, oud.name, source_id)
    for our in ours: 
        source_id = our.dataset.source_id
        our_sources[(our.relation, our.ou1_id)] = source_id
        id_relations[our.relation][our.ou1_id] = our.ou2_id
    outree = dict()
    source_ids = set(oud_sources.values()).union(our_sources.values())
    for k, v in id_relations.items():
        toplevel = set() # toplevel OUs
        rel_ous = dict()
        # build a list of OUs with lists for children, add all OUs to toplevel
        for uid, (shortname, name, source_id) in ous.items():
            rel_ous[uid] = (uid, shortname, name, [], source_id)
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


def latest_userdata():
    latest_userdata = dict()
    for ud in UserData.objects.order_by('dataset__timestamp'):
        latest_userdata[ud.uid] = ud
    return latest_userdata


def ldapactionbatch_at(timestamp=None):
    if timestamp is None:
        timestamp = timezone.now()
    actionbatch = LDAPActionBatch(description=timestamp.isoformat())
    translation_rules, user_rules, group_rules = get_rules()
    users = dict()
    for uid, userdata in latest_userdata().items():
        translated_userdata = userdata.as_translated(translation_rules, timestamp)
        fielddict = defaultdict(list)
        for fieldname, templatestr in user_rules.items():
            print(templatestr)
            t = string.Template(templatestr)
            for datadict in translated_userdata:
                try:
                    fielddict[fieldname].append(t.substitute(datadict))
                except KeyError as e:
                    pass
        users[uid] = fielddict
    return users
    # prepare group data

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

