# APIS MD-02 primeri

Primer dela s SAP na Univerzi v Ljubljani, matični podatki.

Končni cilj je, da matične podatke lahko uvozimo v AD oziroma na njihovi osnovi preuredimo objekte
v AD. Aprila 2023 deluje dovolj dobro, da na FRI lahko napolnimo vsa polja, ki nas zanimajo, in ustvarimo ter napolnimo skupine, ki jih potrebujemo.

Sodelujoči pazite, da ne boste dodajali gesel.

## Zahteve

### Seznam zahtev

Od sistema za prenašanje in vnos matičnih podatkov v AD pričakujemo:

  - Polavtomatično ustvarjanje uporabnikov na osnovi kadrovskih podatkov.
  - Popravljanje lastnosti uporabnikov na osnovi kadrovskih podatkov.
  - Uvrščanje uporabnikov v skupine glede na kadrovske podatke.
  - Ustvarjanje skupin na osnovi kadrovskih podatkov.
  - Vklapljanje in izklapljanje uporabniških računov na osnovi kadrovskih podatkov (predvsem poteka pogodb / zaposlitve).
  - Preprosto dodajanje podatkov za prenos.
  - Preprosto dodajanje pravil za ustvarjanje skupin in dodeljevanje v skupine.
  - Iskanje vira podatka, na osnovi katerega je bila nastavljena uporabniška lastnost ali dodeljeno članstvo v skupini.

### Ustvarjanje uporabnikov

Pri ustvarjanju uporabniških računov je glavni problem, ki ga moramo rešiti, unikatnost uporabniških računov.
Vmesnik mora ponujati spletno storitev, s pomočjo katere lahko kadrovska ali druga služba za ime in priimek dobi predlog
uporabniškega imena, ki ga lahko dodeli uporabniku. Spletna storitev mora vrniti vsaj uporabniško ime in e-poštni naslov.

V času testiranja pričakujemo, da bo ustvarjanje uporabniških računov v domeni računalniških centrov;
kasneje bodo to opravilo prevzeli uporabniki v ostalih oddelkih.

### Preslikava uporabniških podatkov

Lahko se zgodi, da kadrovski evidenci začnemo voditi podatke, ki jih prej nismo ali da v času vpeljave in
testiranja odkrijemo, da v kadrovski evidenci obstajajo podatki, ki bi jih radi imeli v AD, a jih nismo predvideli
ob začetku razvoja. Zato je zaželeno, da je dodajanje pravil za preslikavo kadrovskih podatkov v lastnosti v AD.

Začetek leta 2024 na FRI poznamo naslednje lastnosti, ki jih lahko nastavljamo na osnovi podatkov v kadrovski evidenci:

  - CN
  - SN
  - givenName
  - displayName
  - company
  - name
  - sAMAccountName
  - userPrincipalName
  - mail
  - employeeID
  - title
  - description
  - physicalDeliveryOfficeName
  - telephoneNumber
  - department
  - streetAddress
  - manager
  - displayNamePrintable
  - schacHomeOrganization
  - accountExpires
  - eduPersonPrincipalName
  - PersonalTitle
  - schacPersonalTitle
  - schacHomeOrganization
  - schacPersonalPosition

Poleg naštetih je še vrsta podatkov, ki so nastavljeni na konstante in bi jih vmesnik prav tako lahko nastavil.

### Članstvo v skupinah

Poleg nastavljanja lastnosti uporabnika je nujno, da sistem omogoča dodeljevanje uporabnikov v skupine glede na kadrovske podatke. Dodeljevanje v skupine je pogosto pomembnejše od nastavljanja samih kadrovskih podatkov. Začetek leta 2024 na FRI vemo, da potrebujemo dodeljevanje v skupine na osnovi:

  - Organizacijskih enot, v katerih uporabnik dela.
  - Habilitacije.
  - Delovnega mesta.
  - Funkcije v oddelku.

Verjetno bomo v prihodnosti potrebovali še dodeljevanje glede na:
  - Predmete, pri katerih uporabnik poučuje.
  - Projekte, pri katerih uporabnik sodeluje.


## Implementacije
### PHP

Nekoč je bila tu aplikacija, pisana z uporabo ogrodja [Laravel](https://laravel.com/). Ker je nihče ni potreboval ali vzdrževal, je ni več.

### Python

Aplikacija, pisana z uporabo [django](https://docs.djangoproject.com). Morda jo bomo nekoč predelali v flask, ki je bolj minimalističen.

### JS

Uporablja node.js. Zaenkrat dejansko ne obstaja.
