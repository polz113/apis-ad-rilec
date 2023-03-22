from django.db import models
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from django.conf import settings

import codecs
from collections import defaultdict
import json
import os
import string
import itertools
from urllib.request import Request, urlopen, quote

# Create your models here.

FIELD_DELIMITER='__'


def _get_rules(name=None, timestamp=None):
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, 'translation_rules.json')) as f:
        d = json.load(f)
    oud, relationsd, outree_source_ids = oudicts_at(timestamp)
    ou_shortnames = list()
    ou_names = list()
    ou_parts = list()
    relations = relationsd.get('1001__A002', {})
    for ou_id, ou_data in oud.items():
        shortname = ou_data['shortname']
        ouname = ou_data['name']
        # build a list of parent ids for each ou
        parent = ou_id
        parent_ids = []
        while parent is not None:
            parent_ids.append(parent)
            parent = relations.get(parent, None)
        # turn the list of ids into OUs
        t = string.Template("OU=${shortname}")
        parent_strs = []
        for i in reversed(parent_ids):
            try:
                parent_strs.append(t.substitute(oud[i]))
            except KeyError as e:
                pass
        # now store the names, shortnames and ou_parts
        ou_shortnames.append([ou_id, shortname, {}])
        ou_names.append([ou_id, ouname, {}])
        ou_parts.append([ou_id, ",".join(parent_strs), {}])
    translations = {
        "apis_ou_shortnames": ou_shortnames,
        "apis_ou_names": ou_names,
        "apis_ou_parts": ou_parts,
    }
    d['TRANSLATIONS'].update(translations)
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

def _field_adder(datadict, extra_fields, translations, update_datadict=True):
    new_fields = MultiValueDict()
    for fieldname, rulelist in extra_fields.items():
        for (template, trans_names) in rulelist:
            new_data = _fill_template(datadict, template, trans_names, translations)
            if new_data is not None:
                new_fields[fieldname] = new_data
    if update_datadict:
        datadict.update(new_fields)
        return datadict
    return new_fields


DEFAULT_USER_FIELD_ADDER = _field_adder


class DataSource(models.Model):
    DATA_SOURCES = [('apis', 'Apis'), ('studis', 'Studis')]
    subsource = models.JSONField(default=dict)
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

    def _studis_to_userdata(self, parsed):
        user_fields = list()
        for user in parsed:
            uid = user.get('ul_id_predavatelja', None)
            if uid is None:
                uid = get_uid_by_upn(user['upn'])
                if uid is None:
                    uid='?'
            ud = UserData(dataset=ds, uid=uid)
            ud.save()
            for k, l in user.items():
                if type(l) != list:
                    l = [l]
                for i in l:
                    fields = []      
                    if type(i) == dict:
                        for fkey, fval in i.items():
                            field = {
                                "field": "{}__{}".format(k, fkey),
                                "value": fval,
                            }
                            field.update(field_base)
                            fields.append(field)
                    else:
                        field = {
                            "field": k,
                            "value": i,
                        }
                        field.update(field_base)
                        fields.append(field)
                    for field in fields:
                        if field['value'] is None:
                            continue
                        uf = UserDataField(userdata=ud, **field)
                        user_fields.append(uf)
        if len(user_fields):
            UserDataField.objects.bulk_create(user_fields)

    def _studis_to_datasets(self):
        parsed = self.parsed_json()
        api_url = self.subsource['api_url']
        timestamp = timezone.now()
        ds = DataSet(timestamp=timestamp, source=self)
        ds.save()
        valid_from = timestamp
        valid_to = timestamp + timezone.timedelta(days=365*200)
        field_base = {"changed_t": self.timestamp,
                      "fieldgroup": 0,
                      "valid_from": valid_from,
                      "valid_to": valid_to}
        if api_url.startswith("osebeapi/oseba"):
            self._studis_to_userdata(parsed)
        elif api_url.startswith("sifrantiapi/vrstanazivadelavca"):
            pass
        elif api_url.startswith("sifrantiapi/nazivdelavca"):
            pass
        elif api_url.startswith("sifrantiapi/vrstadelovnegamesta"):
            pass
        elif api_url.startswith("sifrantiapi/delovnomesto"):
            pass
        elif api_url.startswith("sifrantiapi/vrstaoddelka"):
            pass
        elif api_url.startswith("sifrantiapi/oddelek"):
            pass
        elif api_url.startswith("sifrantiapi/funkcijavoddelku"):
            pass
        elif api_url.startswith("sifrantiapi/funkcijepodrocja"):
            pass
        elif api_url.startswith("sifrantiapi/funkcijedelavcev"):
            pass
        elif api_url.startswith("sifrantiapi/semestri"):
            pass
        elif api_url.startswith("sifrantiapi/letniki"):
            pass
        elif api_url.startswith("sifrantiapi/tipivpisa"):
            pass
        elif api_url.startswith("sifrantiapi/nacinistudija"):
            pass
        elif api_url.startswith("sifrantiapi/tipiizvajanjapredmeta"):
            pass
        elif api_url.startswith("sifrantiapi/kadrovskistatusi"):
            pass
        elif api_url.startswith("sifrantiapi/naciniizborapredmeta"):
            pass
        elif api_url.startswith("sifrantiapi/zavodi"):
            pass
        elif api_url.startswith("sifrantiapi/kategorijeoseb"):
            pass
        elif api_url.startswith("sifrantiapi/prostori"):
            pass
        else:
            pass
    def _projekti_to_datasets(self):
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
        # reader = codecs.getreader("utf-8")
        req_url = self.base_url + "/" + url
        # Encode url (replace spaces with %20 etc...)
        req_url = quote(req_url, safe="/:=&?#+!$,;'@()*[]")
        request = Request(req_url, None, self.auth)
        response = urlopen(request)
        # data = json.load(reader(response))
        data = response.read()
        if self.cached:
            self.cached_data[url] = data
        return data


def get_data_studis():
    studis = Studis()
    for api_url in ["osebeapi/oseba?slika=false",
                    "sifrantiapi/vrstanazivadelavca",
                    "sifrantiapi/nazivdelavca",
                    "sifrantiapi/vrstadelovnegamesta",
                    "sifrantiapi/delovnomesto",
                    "sifrantiapi/vrstaoddelka",
                    "sifrantiapi/oddelek",
                    "sifrantiapi/funkcijavoddelku",
                    "sifrantiapi/funkcijepodrocja",
                    "sifrantiapi/funkcijedelavcev",
                    "sifrantiapi/kadrovskistatusi",
                    "sifrantiapi/zavodi",
                    "sifrantiapi/kategorijeoseb",
                    "sifrantiapi/prostori"]:
        d = studis.data(api_url)
        source_d = {"api_url": api_url,
                    "base_url": studis.base_url}
        ds = DataSource(source="studis", 
                        subsource=source_d, 
                        timestamp=timezone.now(),
                        data=d)
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
        common_d = MultiValueDict({"uid": [self.uid]})
        for i in ffields.filter(fieldgroup=None):
            common_d.appendlist(i.field, i.value)
        for i in ffields.exclude(fieldgroup=None):
            if i.fieldgroup is None or i.fieldgroup != prev_fieldgroup:
                if d is not None:
                    dicts.append(d)
                prev_fieldgroup = i.fieldgroup
                d = common_d.copy()
            d.appendlist(i.field, i.value)
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
                                                 update_datadict=True))
            # translated_dicts.append(datadict)
        return translated_dicts

    def groups_at(self, timestamp=None, group_rules=None, translations=None):
        if group_rules is None:
            group_rules = _get_rules('GROUP_RULES')
        if translations is None:
            translations = _get_rules('TRANSLATIONS')
        datadicts = self.with_extra(timestamp=timestamp, translations=translations)
        result = set()
        for fields, flags in group_rules:
            for d in datadicts:
                try:
                    template = fields['distinguishedName']
                    print(template)
                    t = string.Template(template)
                    identifiers = t.get_identifiers()
                    for i in identifiers:
                        print("    ",i,":", d.get(i))
                    data = t.substitute(d)
                    result.add(data.encode('utf-8'))
                except KeyError:
                    pass
        return list(result)

    def by_rules(self, user_rules=None, timestamp=None, extra_fields=None, translations=None):
        if user_rules is None:
            user_rules = _get_rules('USER_RULES')
        if translations is None:
            translations = _get_rules('TRANSLATIONS')
        datadicts = self.with_extra(timestamp=timestamp, extra_fields=extra_fields, translations=translations)
        result = []
        for fieldname, templates in user_rules.items():
            if type(templates) != list:
                templates = [templates]
            values = set()
            for template in templates:
                t = string.Template(template)
                for d in datadicts:
                    try:
                        data = t.substitute(d)
                        values.add(data.encode('utf-8'))
                    except KeyError:
                        pass
            if len(values) > 0:
                result.append([fieldname, list(values)])
        return result
                


def create_groups(timestamp=None, group_rules=None, translations=None):
    if group_rules is None:
        group_rules = _get_rules('GROUP_RULES')
    if translations is None:
        translations = _get_rules('TRANSLATIONS')
    groups = list()
    for field_dict, flags in group_rules:
        create_sources = flags.get("create_sources", {})
        create_fields = flags.get("create_fields", {})
        # get a cartesian product of all translations for this dn_template
        props = list()
        propnames = list()
        for field_name, (mode, args) in create_sources.items():
            if mode == 'translate_keys':
                trans_list = translations.get(args[0], [])
                vals = [i[0] for i in trans_list]
            elif mode == 'translate_values':
                trans_list = translations.get(args[0], [])
                vals = [i[1] for i in trans_list]
            elif mode == 'constant':
                vals = args
            else:
                pass
            props.append(vals)
            propnames.append(field_name)
        # print(propnames, props)
        all_values = itertools.product(*props)
        # create all possible groups
        for vals in all_values:
            d = dict()
            for i, p in enumerate(propnames):
                d[p] = vals[i]
            group_dict = dict()
            for fieldname, template in field_dict.items():
                t1 = string.Template(template)
                d = _field_adder(d, extra_fields=create_fields, translations=translations)
                group_dict[fieldname] = t1.substitute(d)
            groups.append(group_dict)
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


def get_uid_by_upn(upn):
    possible=set(UserDataField.objects.filter(field='Komunikacija__0105__9007__vrednostNaziv', value__iexact=upn).values_list('userdata__uid', flat=True))
    if len(possible) == 1:
        return possible.pop()
    return None


class TranslationTable(models.Model):
    name = models.CharField(max_length=256)
    source = models.ForeignKey('DataSet', null=True, on_delete=models.SET_NULL)
    flags = models.JSONField()


class TranslationRule(models.Model):
    table = models.ForeignKey('TranslationTable', on_delete=models.CASCADE, related_name='rules')
    pattern = models.TextField()
    replacement = models.TextField()
    

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


def latest_userdata(source=None):
    latest_userdata = dict()
    users = UserData.objects.all()
    if source is not None:
        users = users.filter(dataset__source__source=source)
    for ud in users.order_by('dataset__timestamp'):
        latest_userdata[ud.uid] = ud
    return latest_userdata


def ldapactionbatch_at(timestamp=None, source=None):
    if timestamp is None:
        timestamp = timezone.now()
    actionbatch = LDAPActionBatch(description=timestamp.isoformat())
    users = dict()
    groups = dict()
    ous, ou_relations, outree_source_ids = oudicts_at(timestamp)
    for uid, userdata in latest_userdata(source=source).items():
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
        ldap_conn = ldap.initialize(SETTINGS.LDAP_SERVER_URI)
        # ldap_conn.set_option(ldap.OPT_X_TLS_CACERTFILE, '/path/to/ca.pem')
        # ldap_conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
        # ldap_conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        # ldap_conn.start_tls_s()
        ldap_conn.simple_bind_s(settings.LDAP_BIND_DN, settings.LDAP_BIND_PASSWORD)
        ux = ud0.by_rules()
        dn = "test"
        l.add_s("CN=Marko Toplak,CN=Users,DC=test,DC=nodomain", [tuple(i) for i in ux])
        pass

class LDAPAction(models.Model):
    ACTION_CHOICES = [
        ('user_upsert', 'Upsert user data'),
        ('group_upsert', 'Upsert group data'),
        ('add', 'Add'),
        ('modify', 'Modify'),
        ('delete', 'Delete')]
    sources = models.ManyToManyField('DataSet')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    dn = models.TextField()
    data = models.JSONField()
    def apply(self, ldap_conn, user_data):
        pass

class LDAPApply(models.Model):
    batch = models.ForeignKey('LDAPActionBatch', on_delete=models.RESTRICT)
    result = models.JSONField()
    timestamp = models.DateTimeField()

