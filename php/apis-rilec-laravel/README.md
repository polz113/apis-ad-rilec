Aplikacija za črpanje podatkov iz APIS v AD UL.

Ker SAP poleg vsake vrednosti sporoči tudi obdobje veljavnosti,
je ugotavljanje trenutnega stanja kadrovskih podatkov bolj zapleteno,
kot bi si želeli.

# Kako deluje / podatkovni model

Prenos iz SAP v AD se zgodi v treh korakih; med koraki ima operater možnost podatke pregledati in se ustaviti, preden pride do škode:
  - prevzem podatkov od SAP
  - pripravljanje podatkov za vnos v AD
  - sam vnos v AD.

## Prevzem podatkov od SAP

Aplikacija na URL-ju /hr/HRMaster/replicate sprejme podatke v dogovorjenem formatu. Sprejeti podatki se shranijo v tabelo h\_r\_master\_update, nato pa se razbijejo in razbiti shranijo v tabele:
  - o\_u\_data s podatki o organizacijskih enotah,
  - o\_u\_relation s podatkom o nad/podrejenosti enot,
  - user\_data s podatki o uporabnikih.

Ob vsakem podatku so spravljeni datumi / časovne značke njegove veljavnosti ter ID vnosa v h\_r\_master\_update, iz katerega je bil podatek izluščen.

Poleg tega je v user\_data dodano polje dataitem, ki predstavlja zaporedno številko "strukture", v kateri je bil podatek. 
Na primer, če gre za podatke, ki so bili originalno navedeni kot:

```
"Lokacije":{
"infotip": "999999",
"data": [
    { "tip": 1, "naslov": "Ribiška", "st. hiše": 15 },
    { "tip": 2, "naslov": "Lovska", "stanovanje": "Valentinčič" }
},
"Kontakt":{
    infotip: "999998",
    podtip: "preprost",
    data: [{ "ime": "Janez", "priimek": "Novak"}],
}
]
```

Bo v tabeli user\_data nekaj podobnega:
```
[
    {dataitem: 1, property: "Lokacije.99999.0.naslov", value: "Ribiška"}
    {dataitem: 1, property: "Lokacije.99999.0.st_hie", value: 15}
    {dataitem: 2, property: "Lokacije.99999.0.naslov", value: 15}
    {dataitem: 2, property: "Lokacije.99999.0.stanovanje", value: 15}
    {dataitem: 3, property: "Kontakt.99998.preprost.ime", value: "Janez"}
    {dataitem: 3, property: "Kontakt.99998.preprost.priimek", value: "Novak"}
]
```

## Pripravljanje podatkov za vnos v AD

Podatki iz tabele user\_data se ob izvedbi zahteve PUT na URL /api/dataset predelajo v nabor akcij, ki jih moramo izvesti na strežniku LDAP, da se podatki prenesejo. Za vsak nabor akcij se ustvari vnos v tabeli a\_d\_dataset.

Na to tabelo se potem nanašajo vnosi v tabeli LDAPAction, ki vsebujejo same akcije.

Pri predelavi se upoštevata slovarja "TRANSLATION\_TABLE" in
"USER\_TRANSLATION\_RULES", ki se nahajata v app/Http/Controllers/ADDatasetController.php in ki ju lahko v prihodnosti po potrebi premaknemo iz aplikacije v ločeno datoteko.


## Vnos podatkov v AD



# URL-ji

  - /hr/HRMaster/replicate - sprejemna točka za podatke, ob zahtevku GET vrne vse doslej prejete podatke
  - /api/dataset - ustvarjanje nabora podatkov za prenos v AD
  - /api/ldapaction - prenos podatkov v AD
  - /api/ou\_tree/**DATUM** - drevo OU-jev brez zaposlenih
  - /api/userprofile/**DATUM** - seznam zaposlenih
  - /api/userprofile/**DATUM**/**ID_UPORABNIKA** - podrobnosti o zaposlenem
  - /api/ou/**DATUM** - seznam OU-jev
  - /api/ou/**DATUM**/**id** - podrobnosti o skupini

# 
