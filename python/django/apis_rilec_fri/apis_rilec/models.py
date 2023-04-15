from django.db import models
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from django.conf import settings
from django.utils.text import slugify

import traceback

import codecs
from collections import defaultdict
import json
import os
import re
import string
import itertools
import ldap



from urllib.request import Request, urlopen, quote

# Create your models here.

FIELD_DELIMITER='__'

RDN_FIELDS = {'cn', 'name', 'objectCategory'}

def _slugify_username_fn(s):
    return slugify(s)


def _dotty_username_fn(s, **kwargs):
    return ".".join([slugify(i) for i in re.split('[^\w]', s)])


def _letter_and_surname_fn(s, **kwargs):
    l = [slugify(i) for i in re.split('[^\w]', s)]
    if len(l) > 1:
        l = [l[0][0]] + l[1:]
    return "".join(l)


def _name_and_letters_fn(s, **kwargs):
    l = [slugify(i) for i in re.split('[^\w]', s)]
    if len(l) > 1:
        l = l[0:1] + [i[0] for i in l[1:]]
    return "".join(l)


def _first_20_chars(s, **kwargs):
    return s[:20]


def uid_to_dn(uid, ldap_conn, **kwargs):
    try:
        ret = ldap_conn.search_s(settings.LDAP_USER_SEARCH_BASE,
                                     scope=settings.LDAP_USER_SEARCH_SCOPE,
                                     filterstr='employeeId={}'.format(uid),
                                     attrlist=['distinguishedName'])
        assert len(ret) == 1
        dn = ret[0][0]
    except Exception as e:
        dn = None
    return dn


def upn_to_uid(upn, **kwargs):
    if upn is None:
        return None
    possible=set(UserDataField.objects.filter(field='Komunikacija__0105__9007__vrednostNaziv', value__iexact=upn).values_list('userdata__uid', flat=True))
    if len(possible) == 1:
        return possible.pop()
    return None


TRANSLATOR_FUNCTIONS = {
    'default_username': _dotty_username_fn,
    'first_20_chars': _first_20_chars,
    'uid_to_dn': uid_to_dn,
    'upn_to_uid': upn_to_uid,
}


def _tzdate(date):
    if type(date) == str:
        t = timezone.datetime.fromisoformat(date)
    else:
        t = date
    return timezone.make_aware(t)


def _get_rules(name=None, timestamp=None):
    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, 'translation_rules.json')) as f:
        d = json.load(f)
    if name is None or name == 'TRANSLATIONS':
        translations = d.get('TRANSLATIONS', dict())
        for tt in TranslationTable.objects.all():
            translations[tt.name] = {"type": tt.type,
                    "rules": list(tt.rules.order_by('order').values_list('pattern', 'replacement'))}
        translators = dict()
        for tname, tdata in translations.items():
            trules = tdata['rules']
            ttype = tdata['type']
            if ttype == 'dict':
                translator = DictTranslator(trules, use_default=False)
            elif ttype == 'defaultdict':
                translator = DictTranslator(trules, use_default=True)
                pass
            elif ttype == 'substr':
                translator = StrTranslator(trules)
                pass
            elif ttype == 'function':
                # print(ttype, tname)
                translator = FuncTranslator(trules)
            translators[tname] = translator
        d['TRANSLATIONS'] = translators
    if name is None:
        return d
    return d[name]


class StrTranslator():
    def __init__(self, rules):
        self.rules = rules

    def keys(self):
        return list()

    def values(self):
        return list()
    
    def translate(self, s, **kwargs):
        for pattern, replacement in self.rules:
            s = s.replace(pattern, replacement)
        return s


class DictTranslator():
    def __init__(self, rules, use_default=False):
        self.use_default = use_default
        self.d = dict()
        for pattern, replacement in rules:
            self.d[pattern] = replacement

    def keys(self):
        return self.d.keys()

    def values(self):
        return self.d.values()

    def translate(self, s, **kwargs):
        if self.use_default:
            default = self.d.get("", s)
        else:
            default = None
        return self.d.get(s, default)


class FuncTranslator():
    def __init__(self, rules):
        self.fns = list()
        for fname, arg in rules:
            self.fns.append(TRANSLATOR_FUNCTIONS.get(fname, lambda x, **kwargs: x))

    def keys(self):
        return list()

    def values(self):
        return list()
    
    def translate(self, s, **kwargs):
        for fn in self.fns:
            s = fn(s, **kwargs)
        return s


class NoOpTranslator():
    def translate(self, s, **kwargs):
        return s


NOOP_TRANSLATOR=NoOpTranslator()


def _fill_template(datadict, template, trans_names, translations, ldap_conn=None):
    t = string.Template(template)
    try:
        data = t.substitute(datadict)
        for tname in trans_names:
            data = translations.get(tname, NOOP_TRANSLATOR).translate(data, ldap_conn=ldap_conn)
    except KeyError as e:
        # print("Booo, ", template, datadict)
        return None
    return data


def _field_adder(datadict, extra_fields, translations, update_datadict=True,
                 ldap_conn=None):
    if update_datadict:
        d = datadict
        new_fields = datadict
    else:
        d = datadict.copy()
        new_fields = MultiValueDict()
    for fieldname, rulelist in extra_fields:
        for (template, trans_names) in rulelist:
            new_data = _fill_template(d, template, trans_names, translations,
                                      ldap_conn=ldap_conn)
            if new_data is not None:
                d[fieldname] = new_data
                if d is not new_fields:
                    new_fields[fieldname] = new_data
    return new_fields


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
                  'valid_from': _tzdate(valid_from_d),
                  'valid_to': _tzdate(valid_to_d) }
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
                      'changed_t': _tzdate(changed_t),
                      'fieldgroup': fieldgroup,
                      'valid_from': _tzdate(valid_from),
                      'valid_to': _tzdate(valid_to) }
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
                valid_from=_tzdate(subitem.get('veljaOd', valid_from_d)),
                valid_to=_tzdate(subitem.get('veljaDo', valid_to_d)),
                changed_t=_tzdate(subitem.get('datumSpremembe', dataset.timestamp)),
            )
            ou_data_sets.append(oud)
        return ou_data_sets

    def _apis_nadomescanje_to_ourelations(self, dataset, dataitem):
        ou_relations = list()
        valid_from_d = dataitem.get('veljaOd')
        valid_to_d = dataitem.get('veljaDo')
        relation = FIELD_DELIMITER.join(['N', dataitem.get('infotip', '0000'),
                                         dataitem.get('podtip', '0000')])
        uid = dataitem['sistemiziranoMesto_Id']
        for subitem in dataitem['data']:
            our = OURelation(
                dataset=dataset,
                valid_from=_tzdate(subitem.get('veljaOd', valid_from_d)),
                valid_to=_tzdate(subitem.get('veljaDo', valid_to_d)),
                relation=relation,
                ou1_id=uid,
                ou2_id=subitem['id'],
            )
            ou_relations.append(our)
        return ou_relations

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
                valid_from=_tzdate(subitem.get('veljaOd', valid_from_d)),
                valid_to=_tzdate(subitem.get('veljaDo', valid_to_d)),
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
        ds, created = DataSet.objects.get_or_create(timestamp=timestamp, source=self)
        if not created:
            ds.oudata_set.all().delete()
            ds.ourelation_set.all().delete()
            ds.translationtable_set.all().delete()
        ou_data = list()
        ou_relations = list()
        for k, v in in_data.items():
            if type(v) == list:
                for dataitem in v:
                    if k == 'OE':
                        ou_data += self._apis_to_oudata(ds, dataitem)
                    elif k == 'NadrejenaOE':
                        ou_relations += self._apis_to_ourelations(ds, dataitem)
                    elif k == 'Nadomescanje':
                        ou_relations += self._apis_nadomescanje_to_ourelations(ds, dataitem)
                    else:
                        uid = dataitem.get('UL_Id', None)
                        if uid is None:
                            continue
                        else:
                            user_dicts[uid] += self._apis_to_userdatadicts(timestamp, k, dataitem)
        user_fields = list()
        # Create UserData and fields from user_dicts
        for uid, fieldlist in user_dicts.items():
            ud, created = UserData.objects.get_or_create(dataset=ds, uid=uid)
            if not created:
                ud.fields.all().delete()
            for fields in fieldlist:
                uf = UserDataField(userdata=ud, **fields)
                user_fields.append(uf)
        if len(user_fields):
            UserDataField.objects.bulk_create(user_fields)
        # Done filling users. Handle OUs
        OUData.objects.bulk_create(ou_data)
        OURelation.objects.bulk_create(ou_relations)

    def _studis_to_userdata(self, dataset, parsed):
        user_fields = list()
        dataset.userdata_set.all().delete()
        for user in parsed:
            uid = user.get('ul_id_predavatelja', None)
            if uid is None:
                uid = upn_to_uid(user['upn'])
                if uid is None:
                    uid='?'
            # ud, created = UserData.objects.get_or_create(dataset=dataset, uid=uid)
            # if not created:
            #     ud.fields.all().delete()
            ud = UserData(dataset=dataset, uid=uid)
            ud.save()
            for k, l in user.items():
                if type(l) != list:
                    l = [l]
                    set_fieldgroup = False
                else:
                    set_fieldgroup = True
                for i, value in enumerate(l):
                    fields = []      
                    if type(value) == dict:
                        for fkey, fval in value.items():
                            fields.append({
                                "field": "{}__{}".format(k, fkey),
                                "value": fval,
                            })
                    else:
                        fields.append({
                            "field": k,
                            "value": value,
                        })
                    for field in fields:
                        if field['value'] is None:
                            continue
                        if set_fieldgroup:
                            fieldgroup = i
                        else:
                            fieldgroup = None
                        uf = UserDataField(userdata=ud,
                                           fieldgroup=fieldgroup,
                                           valid_from=self.timestamp,
                                           valid_to=self.timestamp + timezone.timedelta(days=365000),
                                           **field)
                        user_fields.append(uf)
        if len(user_fields):
            UserDataField.objects.bulk_create(user_fields)

    def _studis_to_translations(self, dataset, table_prefix, parsed):
        prefix = 'studis__' + table_prefix
        rules = defaultdict(list)
        for d in parsed:
            pattern = d.pop('id')
            if pattern is None:
                continue
            for k, v in d.items():
                if v is None:
                    continue
                table_name = prefix + '__' + k
                if type(v) == dict:
                    for sub_k, sub_v in v.items():
                        if sub_v is None:
                            continue
                        rtable_name = table_name + '__' + sub_k
                        rules[rtable_name].append(TranslationRule(pattern = pattern, replacement = sub_v))
                else:
                    rules[table_name].append(TranslationRule(pattern = pattern, replacement = v))
        for table_name, rule_list in rules.items():
            t, created = TranslationTable.objects.get_or_create(name=table_name, dataset=dataset, 
                    defaults={"type": 'defaultdict'})
            if not created:
                t.rules.all().delete()
            for i, r in enumerate(rule_list):
                r.table = t
                r.order = i
            TranslationRule.objects.bulk_create(rule_list)

    def _studis_to_datasets(self):
        parsed = self.parsed_json()
        api_url = self.subsource['api_url']
        # timestamp = timezone.now()
        timestamp = self.timestamp
        ds, created = DataSet.objects.get_or_create(timestamp=timestamp, source=self)
        valid_from = timestamp
        valid_to = timestamp + timezone.timedelta(days=365*200)
        field_base = {"changed_t": self.timestamp,
                      "fieldgroup": 0,
                      "valid_from": valid_from,
                      "valid_to": valid_to}
        if api_url.startswith("osebeapi/oseba"):
            self._studis_to_userdata(ds, parsed)
        elif api_url.startswith("sifrantiapi"):
            table_prefix = api_url.split('/')[1]
            self._studis_to_translations(ds, table_prefix, parsed)
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
                # print(d)
                d = common_d.copy()
            d.appendlist(i.field, i.value)
        if d is not None:
            dicts.append(d)
        return dicts

    def with_extra(self, timestamp=None, extra_fields=None, translations=None,
                   ldap_conn=None):
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
                                                 update_datadict=True,
                                                 ldap_conn=ldap_conn))
            # translated_dicts.append(datadict)
        return translated_dicts

    def groups_at(self, timestamp=None, group_rules=None, translations=None,
                  ldap_conn=None):
        if group_rules is None:
            group_rules = _get_rules('GROUP_RULES')
        if translations is None:
            translations = _get_rules('TRANSLATIONS')
        datadicts = self.with_extra(timestamp=timestamp, translations=translations,
                                    ldap_conn=ldap_conn)
        result = set()
        default_dn = None
        for fields, flags in group_rules:
            for d in datadicts:
                try:
                    template = fields['distinguishedName']
                    t = string.Template(template)
                    group_dn = t.substitute(d)
                    if flags.get('main_ou', False):
                        default_dn = group_dn
                    else:
                        result.add(group_dn)
                except KeyError as e:
                    print("  fail:", e)
                    pass
        return default_dn, list(result)

    def by_rules(self, timestamp=None, user_rules=None, extra_fields=None, translations=None,
                 ldap_conn=None):
        if user_rules is None:
            user_rules = _get_rules('USER_RULES')
        if translations is None:
            translations = _get_rules('TRANSLATIONS')
        datadicts = self.with_extra(timestamp=timestamp, extra_fields=extra_fields, 
                translations=translations,
                                    ldap_conn=ldap_conn)
        result = dict()
        for fieldname, templates in user_rules.items():
            if type(templates) != list:
                templates = [templates]
            values = set()
            for template in templates:
                t = string.Template(template)
                for d in datadicts:
                    try:
                        data = t.substitute(d)
                        values.add(data)
                    except KeyError:
                        pass
            if len(values) > 0:
                result[fieldname] = list(values)
        return result
                

def get_groups(timestamp=None, group_rules=None, translations=None, ldap_conn=None):
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
                vals = translations.get(args[0], dict()).keys()
            elif mode == 'translate_values':
                vals = translations.get(args[0], dict()).values()
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
            for fieldname, templatex in field_dict.items():
                if type(templatex) is not list:
                    templatel = [templatex]
                else:
                    templatel = templatex
                value_l = []
                for template in templatel:
                    t1 = string.Template(template)
                    d = _field_adder(d, extra_fields=create_fields, translations=translations,
                                     ldap_conn=ldap_conn)
                    value_l.append(t1.substitute(d))
                group_dict[fieldname] = value_l
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


class TranslationTable(models.Model):
    TRANSLATOR_TYPES = [
            ('dict', 'Dictionary'),
            ('defaultdict', 'Dictionary with default value'),
            ('substr', 'Replace pattern with replacement'),
            ('function', 'Function from TRANSLATOR_FUNCTIONS')
        ]
    def __str__(self):
        return "{} ({})".format(self.name, self.dataset)
    name = models.CharField(max_length=256)
    type = models.CharField(max_length=32, choices=TRANSLATOR_TYPES)
    dataset = models.ForeignKey('DataSet', null=True, blank=True, on_delete=models.SET_NULL)
    flags = models.JSONField(default=dict, blank=True)


class TranslationRule(models.Model):
    def __str__(self):
        return "{} -> {}".format(self.pattern, self.replacement)
    table = models.ForeignKey('TranslationTable', on_delete=models.CASCADE, related_name='rules')
    order = models.IntegerField(default=0)
    pattern = models.TextField(blank=True)
    replacement = models.TextField()
    

def oudicts_at(timestamp=None):
    if timestamp is None:
        timestamp = timezone.now()
    ouds = OUData.objects.filter(valid_to__gte=timestamp,
                                 valid_from__lte=timestamp)
    ours = OURelation.objects.filter(valid_to__gte=timestamp,
                                 valid_from__lte=timestamp)
    ous = dict()
    id_relations = defaultdict(lambda: defaultdict(set))
    oud_sources = dict()
    our_sources = dict()
    for oud in ouds:
        source_id = oud.dataset.source_id
        oud_sources[oud.uid] = source_id
        ous[oud.uid] = {"shortname": oud.shortname, "name": oud.name, "source": source_id}
    for our in ours:
        source_id = our.dataset.source_id
        our_sources[(our.relation, our.ou1_id)] = source_id
        id_relations[our.relation][our.ou1_id].add(our.ou2_id)
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
        for child_id, parent_ids in v.items():
            parent_id = parent_ids.pop()
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


def __dict_to_translations(name, rules, type='defaultdict', 
                           add_only=False, keep_default=True):
    tt, created = TranslationTable.objects.get_or_create(name=name, 
                        defaults={'type': type})
    if not created and not add_only:
        if keep_default:
            tt.rules.exclude(pattern='').delete()
        else:
            tt.rules.all().delete()
    tt_rules = []
    for order, (pattern, replacement) in enumerate(rules):
        tt_rules.append(TranslationRule(table=tt, order=order,
                                        pattern=pattern,
                                        replacement=replacement))
    TranslationRule.objects.bulk_create(tt_rules)


def _apis_relations_to_outree(oud, relations):
    ou_parts = list()
    escaped_oud = dict()
    for ou_id, ou_data in oud.items():
        escaped_oud[ou_id] = dict()
        for k, v in ou_data.items():
            escaped_oud[ou_id][k] = ldap.dn.escape_dn_chars(str(v))
    for ou_id, ou_data in oud.items():
        # build a list of parent ids for each ou
        parent = ou_id
        parent_ids = []
        while parent is not None:
            parent_ids.append(parent)
            parents = relations.get(parent, set())
            if len(parents) > 0:
                parent = list(parents)[0]
            else:
                break
        # turn the list of ids into OUs
        t = string.Template("OU=${shortname}")
        parent_strs = []
        for i in reversed(parent_ids):
            try:
                parent_strs.append(t.substitute(escaped_oud[i]))
            except KeyError as e:
                pass
        # now store the names, shortnames and ou_parts
        ou_parts.append([ou_id, ",".join(parent_strs)])
    return ou_parts


def _apis_field_uid_map(timestamp, field):
    pos_map = defaultdict(set)
    position_fields = UserDataField.objects.filter(
        field = field,
        valid_from__lte = timestamp,
        valid_to__gte = timestamp,
    )
    for f in position_fields:
        # percentage_f = f.userdata.fields.filter()
        pos_map[f.value].add(f.userdata.uid)
    return pos_map


def _apis_relations_to_ou_managers(oud, relations, timestamp=None):
    if timestamp is None:
        timestamp = timezone.now()
    ou_managers = list()
    position_uid_map = _apis_field_uid_map(timestamp, "OrgDodelitev__0001__0__glavnaOrganizacijskaEnota_Id")
    for ou_id, ou_data in oud.items():
        for supervisor_position in relations.get(ou_id, set()):
            supervisor_uids = position_uid_map[supervisor_position]
        if len(supervisor_uids) != 1:
            continue
        else:
            supervisor_uids = list(supervisor_uids)[0]
        for supervisor_uid in supervisor_uids:
            ou_managers.append([ou_id, supervisor_uid])
    return ou_managers


def _apis_relations_to_uid_managers(oud, relationsd, timestamp=None):
    if timestamp is None:
        timestamp = timezone.now()
    position_uids_dict = _apis_field_uid_map(timestamp, "Razporeditev__1001__B008__sistemiziranoMesto_Id")
    position_uid_dict = dict()
    for position, uids in position_uids_dict.items():
        position_uid_dict[position] = list(uids)[0]
    ou_uid_dict = _apis_field_uid_map(timestamp, "OrgDodelitev__0001__0__glavnaOrganizacijskaEnota_Id")
    uid_ou_dict = dict()
    for ouid, uids in ou_uid_dict.items():
        for uid in uids:
            uid_ou_dict[uid] = ouid
    ou_manager_relations = relationsd.get('1001__B012', dict())
    ou_managers = defaultdict(set)
    for ouid, manager_positions in ou_manager_relations.items():
        for pos in manager_positions:
            ou_managers[ouid].add(position_uid_dict.get(pos, None))
            ou_managers[ouid].discard(None)
    explicit_managers = relationsd.get('N__1001__A002', dict())
    # TODO: set managers
    managers = dict()
    for position, uid in position_uid_dict.items():
        # N__1001__AR01 je dejansko nadomescanje, N__1001__A002 je eksplicitni nadrejeni
        explicit_manager = explicit_managers.get(position, None)
        if explicit_manager is not None:
            managers[uid] = position_uid_dict[list(explicit_manager)[0]]
            continue
        ouid = uid_ou_dict.get(uid, None)
        cur_managers = ou_managers.get(ouid, None)
        # print("uid:", uid, "ou:", ouid, "managers:", cur_managers)
        while cur_managers is not None and\
                uid in cur_managers:
            parent_ouids = relationsd.get('1001__A002', dict()).get(ouid, {None})
            parent_ouid = list(parent_ouids)[0]
            # print("parent ou:", parent_ouid)
            cur_managers = ou_managers.get(parent_ouid, None)
            ouid = parent_ouid
        if cur_managers is not None and len(cur_managers) == 1:
            managers[uid] = list(cur_managers)[0]
    return list(managers.items())


def apis_to_translations(timestamp=None,
                         add_only=False, keep_default=True):
    if timestamp is None:
        timestamp = timezone.now()
    oud, relationsd, outree_source_ids = oudicts_at(timestamp)
    ou_shortnames = list()
    ou_names = list()
    for ou_id, ou_data in oud.items():
        ou_shortnames.append([ou_id, ou_data['shortname']])
        ou_names.append([ou_id, ou_data['name']])
    ou_relations = relationsd.get('1001__A002', {})
    ou_manager_relations = relationsd.get('1001__B012', {})
    trans_dict = {
        "apis_ou__shortname": ou_shortnames,
        "apis_ou__name": ou_names,
        "apis_ou_parts": _apis_relations_to_outree(oud, ou_relations),
        "apis_ou_managers": _apis_relations_to_ou_managers(oud, 
                ou_manager_relations, timestamp),
        "apis_uid_managers": _apis_relations_to_uid_managers(oud,
                relationsd, timestamp),
    }
    for k, v in trans_dict.items():
        __dict_to_translations(k, v, type='defaultdict',
                               add_only=add_only, keep_default=keep_default)


def latest_userdata(source=None):
    latest_userdata = dict()
    users = UserData.objects.all()
    if source is not None:
        users = users.filter(dataset__source__source=source)
    for ud in users.order_by('dataset__timestamp'):
        latest_userdata[ud.uid] = ud
    return latest_userdata


def get_ad_user_dn(ldap_conn, user_fields):
    for i in ['employeeId', 'userPrincipalName']:
        try:
            # TODO: proper escaping
            filterstr = "{}={}".format(i, user_fields[i][0])
            # print("search", filterstr)
            ret = ldap_conn.search_s(settings.LDAP_USER_SEARCH_BASE,
                                     scope=settings.LDAP_USER_SEARCH_SCOPE,
                                     filterstr=filterstr,
                                     attrlist=['distinguishedName'])
            # print("returning", ret)
            assert len(ret) == 1
            return(ret[0][0])
        except Exception as e:
            # print(e)
            # traceback.print_exception(e)
            # print(user_fields)
            pass
    return user_fields.get('distinguishedName', None)


def group_ldapactionbatch(timestamp=None):
    if timestamp is None:
        timestamp = timezone.now()
    actionbatch = LDAPActionBatch(description=timestamp.isoformat())
    users = dict()
    groups = dict()
    ous, ou_relations, outree_source_ids = oudicts_at(timestamp)
    actions = list()
    # prepare groups
    for order, group in enumerate(get_groups(timestamp=timestamp)):
        dn = group.pop('distinguishedName')[0]
        action = LDAPAction(action='upsert', dn=dn, data=group)
        actions.append(action)
    actionbatch.save()
    for i, action in enumerate(actions):
        action.batch = actionbatch
        action.order = i
    LDAPAction.objects.bulk_create(actions)
    return actionbatch
    

def user_ldapactionbatch(userdata_set, timestamp=None, ldap_conn=None,
                         rename_users=False, empty_groups=True):
    if timestamp is None:
        timestamp = timezone.now()
    extra_fields = _get_rules('EXTRA_FIELDS')
    translations = _get_rules('TRANSLATIONS')
    group_rules = _get_rules('GROUP_RULES')
    actionbatch = LDAPActionBatch(description=timestamp.isoformat())
    groups_membership = MultiValueDict()
    actions = list()
    users = dict()
    for userdata in userdata_set:
        uid = userdata.uid
        default_group_dn, groups_to_join = userdata.groups_at(timestamp, translations=translations, group_rules=group_rules)
        user_fields = userdata.by_rules(timestamp, translations=translations, extra_fields=extra_fields,
                                        ldap_conn=ldap_conn)
        default_dn="CN={},{}".format(ldap.dn.escape_dn_chars(user_fields['cn'][0]), default_group_dn)
        existing_dn = get_ad_user_dn(ldap_conn, user_fields)
        if existing_dn is not None:
            for rdn_field in RDN_FIELDS:
                user_fields.pop(rdn_field)
            if rename_users:
                actions.append(LDAPAction(action='rename',
                    dn=existing_dn, data={'distinguishedName': [default_dn]}))
                final_dn = default_dn
            else:

                final_dn = existing_dn
        else:
            final_dn = default_dn
        actions.append(LDAPAction(action='upsert', dn=final_dn, 
                                  data=user_fields))
        for group_dn in groups_to_join:
            # TODO add user DN to group property "member"
            groups_membership.appendlist(group_dn, final_dn)
    for group_dn, user_list in groups_membership.lists():
        membership = {'member': user_list}
        if empty_groups:
            # replace the user list
            actions.append(LDAPAction(action='modify', dn=group_dn,
                                      data=membership))
        else:
            # extend the user list
            actions.append(LDAPAction(action='add', dn=group_dn, 
                                      data=membership))
    actionbatch.save()
    for i, action in enumerate(actions):
        action.batch = actionbatch
        action.order = i
    LDAPAction.objects.bulk_create(actions)
    return actionbatch


class LDAPActionBatch(models.Model):
    description = models.CharField(max_length=512, blank=True, default='')
    def apply(self):
        ldap_conn = ldap.initialize(settings.LDAP_SERVER_URI)
        # ldap_conn.set_option(ldap.OPT_X_TLS_CACERTFILE, '/path/to/ca.pem')
        # ldap_conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
        # ldap_conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        # ldap_conn.start_tls_s()
        ldap_conn.simple_bind_s(settings.LDAP_BIND_DN, settings.LDAP_BIND_PASSWORD)
        for i in self.actions.all():
            apply = i.apply(ldap_conn)
        #dn = "test"
        #ux = ud0.by_rules()
        #l.add_s("CN=Marko Toplak,CN=Users,DC=test,DC=nodomain", [tuple(i) for i in ux])
        pass


class LDAPAction(models.Model):
    ACTION_CHOICES = [
        ('upsert', 'Upsert (add or modify)'),
        ('add', 'Add'),
        ('modify', 'Modify'),
        ('rename', 'Rename'),
        ('delete', 'Delete')]
    order = models.IntegerField(default=0)
    batch = models.ForeignKey('LDAPActionBatch', related_name='actions', on_delete=models.CASCADE)
    sources = models.ManyToManyField('DataSet')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    dn = models.TextField()
    data = models.JSONField()
    flags = models.JSONField(blank=True, default=dict)

    def _upsert(self, ldap_conn):
        try:
            exists = ldap_conn.compare_s(self.dn,
                                         'distinguishedName', self.dn)
        except Exception as e:
            print(e)
            exists = False
        if exists:
            for k in RDN_FIELDS:
                self.data.pop(k, None)
            return self._modify(ldap_conn)
        else:
            return self._add(ldap_conn)

    def _add(self, ldap_conn):
        ul = []
        for k, l in self.data.items():
            ul.append((k, [i.encode('utf-8') for i in l]))
        ldap_conn.add_s(self.dn, ul)

    def _modify(self, ldap_conn):
        ul = []
        for k, l in self.data.items():
            ul = []
            try:
                ul.append((ldap.MOD_REPLACE, k, [i.encode('utf-8') for i in l]))
                ldap_conn.modify_s(self.dn, ul)
            except Exception as e:
                print("failed:", k)
                print(e)

    def _rename(self, ldap_conn):
        new_dn = self.data['distinguishedName']
        ldap_conn.rename_s(self.dn, new_dn)

    def _delete(self, ldap_conn):
        ldap_conn.delete_s(self.dn)

    def apply(self, ldap_conn):
        apply_fns = {
            'upsert': self._upsert,
            'add': self._add,
            'modify': self._modify,
            'rename': self._modify,
            'delete': self._delete,
        }
        return(apply_fns[self.action](ldap_conn))
 

class LDAPApply(models.Model):
    batch = models.ForeignKey('LDAPActionBatch', on_delete=models.RESTRICT)
    result = models.JSONField()
    timestamp = models.DateTimeField()

