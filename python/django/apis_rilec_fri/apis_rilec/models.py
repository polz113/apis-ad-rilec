from django.db import models
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

from collections import defaultdict
import json
import string
import os


# Create your models here.

FIELD_DELIMITER='__'


def _get_rules(name=None):
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, 'translation_rules.json')) as f:
        d = json.load(f)
    if name is None:
        return d
    return d[name]


"""rules are typically handled one-by-one.
However, if all rules but the last are final and apply
to whole strings, the translation can be reduced to a
simple dict lookup.
"""
def _make_translator(rules):
    if len(rules) == 0:
        return lambda x: x
    default_flags = {
        "default": False,
        "substring": False,
        "finish": True
    }
    def _translate_linear(s):
        for needle, repl, in_flags in rules:
            flags = default_flags.copy()
            flags.update(in_flags)
            if flags['default']:
                return repl
            matched = False
            if flags['substring']:
                matched = s.find(needle) > -1
                s.replace(needle, repl)
            elif s == needle:
                matched = True
                s = repl
            if matched and flags['finish']:
                return s
        return s
    trans_dict = dict()
    for needle, repl, in_flags in rules[:-1]:
        flags = default_flags.copy()
        flags.update(in_flags)
        if flags['substring'] or not flags['finish']:
            return _translate_linear
        trans_dict[needle] = repl
    needle, repl, in_flags = rules[-1]
    flags = default_flags.copy()
    flags.update(in_flags)
    if flags['substring']:
        return lambda s: trans_dict.get(s, s).replace(needle, repl)
    elif flags['default']:
        return lambda s: trans_dict.get(s, repl)
    else:
        trans_dict[needle] = repl
        return lambda s: trans_dict.get(s, s)


def _fill_template(datadict, template, trans_names, translations):
    translators = list()
    for tname in trans_names:
        rules = translations.get(tname, [])
        translators.append(_make_translator(rules))
    t = string.Template(template)
    try:
        data = t.substitute(datadict)
        for translator in translators:
            data = translator(data)
    except KeyError as e:
        # print("Booo, ", template, datadict)
        return None
    return data

def _field_adder(datadict, extra_fields, translations, source=None, update_datadict=True):
    new_fields = dict()
    for fieldname, rulelist in extra_fields.items():
        for (fsource, template, trans_names) in rulelist:
            if fsource is not None and fsource != source:
                continue
            new_data = _fill_template(datadict, template, trans_names, translations)
            if new_data is not None:
                new_fields[fieldname] = new_data
    if update_datadict:
        datadict.update(new_fields)
        return datadict
    return new_fields

"""
def field_adder_factory():
    translations = __get_rules('TRANSLATIONS')
    extra_fields = __get_rules('EXTRA_FIELDS')
    field_add_functions = dict()
    for fieldname, (template, trans_names) in extra_fields.items():
        t = string.Template(template)
        translators = list()
        for tname in trans_names:
            rules = translations.get(tname, [])
            translators.append(__make_translator(rules))
        def __field_add(datadict):
            try:
                print(t.template)
                data = t.substitute(datadict)
                # print("Yaaay, ", data)
                # for translator in translators:
                #     data = translator(data)
            except KeyError as e:
                # print("Booo, ", template, datadict)
                return None
            return data
        field_add_functions[fieldname] = __field_add
    def __field_adder(datadict):
        for fieldname, field_add_fn in field_add_functions.items():
            new_data = field_add_fn(datadict)
            if new_data is not None:
                datadict[fieldname] = new_data
        return datadict
    return __field_adder
"""

DEFAULT_USER_FIELD_ADDER = _field_adder


class DataSource(models.Model):
    DATA_SOURCES = [('apis', 'Apis'), ('studis', 'Studis')]
    source = models.CharField(max_length=32, choices=DATA_SOURCES)
    timestamp = models.DateTimeField()
    data = models.BinaryField()
    
    def parsed_json(self):
        return json.loads(self.data)
    
    def _apis_to_userdatadicts(self, timestamp, prefix, dataitem):
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

    def _apis_to_oudata(self, dataset, dataitem):
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

    def _apis_to_ourelations(self, dataset, dataitem):
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
    
    def _apis_to_datasets(self):
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
                        ou_data += self._apis_to_oudata(ds, dataitem)
                    elif k == 'NadrejenaOE':
                        ou_relations += self._apis_to_ourelations(ds, dataitem)
                    else:
                        uid = dataitem.get('UL_Id', None)
                        if uid is None:
                            continue
                        else:
                            user_dicts[uid] += self._apis_to_userdatadicts(timestamp, k, dataitem)
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

    def _studis_to_datasets(self):
        # TODO implement this
        parsed = self.parsed_json()
        data = parsed['data']
        api_url = parsed['api_url']
        if api_url.startswith("osebeapi/oseba"):
            pass
        elif api_url.startswith("sifrantiapi/nazivdelavca"):
            pass
        elif api_url.startswith("sifrantiapi/oddelek"):
            pass
        elif api_url.startswith("sifrantiapi/funkcijavoddelku"):
            pass
        else:
            pass
        pass

    def _to_datasets_projekti(self):
        # TODO implement projekti, then this
        pass

    def to_datasets(self):
        handlers = {
            'apis': self._apis_to_datasets,
            'studis': self._studis_to_datasets,
            'projekti': self._projekti_to_datasets,
        }
        return handlers[self.source]()


class Studis:
    def __init__(self, cached=True):
        token = settings.STUDIS_API_TOKEN
        self.base_url = settings.STUDIS_API_BASE_URL
        self.auth = {'Content-Type': 'application/json',
                     'AUTHENTICATION_TOKEN': token}
        self.cached = cached
        self.cached_data = dict()

    def data(self, url):
        if self.cached and url in self.cached_data:
            return self.cached_data[url]
        reader = codecs.getreader("utf-8")
        req_url = self.base_url + "/" + url
        # Encode url (replace spaces with %20 etc...)
        req_url = quote(req_url, safe="/:=&?#+!$,;'@()*[]")
        request = Request(req_url, None, self.auth)
        response = urlopen(request)
        data = json.load(reader(response))
        if self.cached:
            self.cached_data[url] = data
        return data


def get_data_studis():
    studis = Studis()
    for api_url in ["osebeapi/oseba",
                    "sifrantiapi/oddelek",
                    "sifrantiapi/funkcijavoddelku"]:
        d = studis.data(api_url)
        ds = DataSource(source="studis", timestamp=timezone.now(),
                data=json.dumps({
                    "api_url": api_url,
                    "base_url": studis.base_url,
                    "data": d,
                })
            )
        ds.save()


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

    def with_extra(self, timestamp=None, extra_fields=None, translations=None):
        translated_dicts = list()
        if extra_fields is None:
            extra_fields = _get_rules('EXTRA_FIELDS')
        if translations is None:
            translations = _get_rules('TRANSLATIONS')
        # this would reload the rules every time the function is run.
        # extra_user_field_gen = extra_user_field_gen_factory()
        source = self.dataset.source.source
        for datadict in self.as_dicts(timestamp=timestamp):
            translated_dicts.append(_field_adder(datadict,
                                                 extra_fields=extra_fields, 
                                                 translations=translations,
                                                 source=source,
                                                 update_datadict=True))
            # translated_dicts.append(datadict)
        return translated_dicts

    def groups_at(self, timestamp=None, group_rules=None, translations=None):
        if group_rules is None:
            group_rules = _get_rules('GROUP_RULES')
        if translations is None:
            translations = _get_rules('TRANSLATIONS')
        oud, relationsd, outree_source_ids = oudicts_at(timestamp)
        datadicts = self.with_extra(timestamp)
        groups = dict()
        joined_groups = list()
        for field_dict, flags in group_rules:
            outree_rules = flags.get("outrees", [])
            tree_fields = dict()
            for datadict in datadicts:
                # Fill ou tree based groups
                parent_dicts = [ datadict.copy() ]
                for tree_rule in outree_rules:
                    key = _fill_template(datadict, tree_rule['key'], [], translations)
                    if key is None:
                        continue
                    relations = relationsd[tree_rule['relation']]
                    field_templates = tree_rule['fields']
                    parent = key
                    parent_ids = []
                    while parent is not None:
                        parent_ids.append(parent)
                        parent = relations.get(parent, None)
                    t = string.Template(tree_rule['part_template'])
                    for i in reversed(parent_ids):
                        try:
                            f_oud = datadict.copy()
                            f_oud.update(oud[i])
                            parent_strs.append(t.substitute(f_oud))
                            f_oud['ou_dn_part'] = ",".join(parent_strs)
                            template_dict = datadict.copy()
                            for field, fkey in field_templates.items():
                                template_dict[field] = f_oud[fkey]
                        except KeyError as e:
                            pass
                for pdict in parent_dicts:
                    # print(pdict)
                    # fill the actual groups
                    group = _field_adder(pdict,
                                         extra_fields=field_dict,
                                         translations=translations,
                                         update_datadict=False)
                    if 'distinguishedName' in group:
                        groups[group['distinguishedName']] = group
        return groups


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


def oudicts_at(timestamp=None):
    if timestamp is None:
        timestamp = timezone.now()
    ouds = OUData.objects.filter(valid_to__gte=timestamp,
                                 valid_from__lte=timestamp)
    ours = OURelation.objects.filter(valid_to__gte=timestamp,
                                 valid_from__lte=timestamp)
    ous = dict()
    id_relations = defaultdict(dict)
    oud_sources = dict()
    our_sources = dict()
    for oud in ouds:
        source_id = oud.dataset.source_id
        oud_sources[oud.uid] = source_id
        ous[oud.uid] = {"shortname": oud.shortname, "name": oud.name, "source": source_id}
    for our in ours: 
        source_id = our.dataset.source_id
        our_sources[(our.relation, our.ou1_id)] = source_id
        id_relations[our.relation][our.ou1_id] = our.ou2_id
        #if our.ou2_id not in ous:
        #    ous[our.ou2_id] = {"uid": our.ou2_id, "shortname": None, "name": None, "source": source_id}
        # add missing parents
    source_ids = set(oud_sources.values()).union(set(our_sources.values()))
    return ous, id_relations, source_ids


def outrees_at(timestamp=None):
    outree = dict()
    ous, id_relations, source_ids = oudicts_at(timestamp)
    for k, v in id_relations.items():
        toplevel = set() # toplevel OUs
        rel_ous = dict()
        # build a list of OUs with lists for children, add all OUs to toplevel
        for uid, ou_data in ous.items():
            d = { "uid": uid,
                  "children": []}
            d.update(ou_data)
            rel_ous[uid] = d
            toplevel.add(uid)
        # remove OUs with parents from toplevel, build children lists
        for child_id, parent_id in v.items():
            rel_ous[child_id]["parent"] = parent_id
            if parent_id in rel_ous:
                toplevel.discard(child_id)
                rel_ous[parent_id]["children"].append(rel_ous[child_id])
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
    users = dict()
    groups = dict()
    ous, ou_relations, outree_source_ids = oudicts_at(timestamp)
    for uid, userdata in latest_userdata().items():
        users[uid] = userdata.with_extra(timestamp)
        groups_to_join = userdata.groups_at(timestamp, ou_trees=ou_trees)
        for group in groups_to_join:
            dn = group['distinguishedName']
            old_group = groups.get(dn, dict())
            # merge the group data, old data has priority
            group.update(old_group)
            groups[dn] = group
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

