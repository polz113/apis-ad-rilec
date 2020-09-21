Aplikacija za črpanje podatkov iz APIS v AD UL.

Ker SAP poleg vsake vrednosti sporoči tudi obdobje veljavnosti,
je ugotavljanje trenutnega stanja organigrama bolj zapleteno,
kot bi si želel.

# URL-ji

  - /hr/HRMaster/replicate - sprejemna točka za podatke, dump vseh podatkov
  - /api/ou\_tree/**DATUM** - drevo OU-jev brez zaposlenih
  - /api/user\_tree/**DATUM** - drevo OU-jev z zaposlenimi vred
  - /api/userprofile/**DATUM** - seznam zaposlenih
  - /api/userprofile/**DATUM**/**ID_UPORABNIKA** - podrobnosti o zaposlenem
  - /api/ou/**DATUM** - seznam OU-jev
  - /api/ou/**DATUM**/**id** - podrobnosti o skupini
