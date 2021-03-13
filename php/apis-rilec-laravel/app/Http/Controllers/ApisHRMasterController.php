<?php

namespace App\Http\Controllers;

use App\HRMasterUpdate;
use App\UserData;
use App\GroupAssignment;
use App\OUData;
use App\OURelation;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Datetime;

define("FIELDNAME_DELIMITER", "/");
define("GROUPNAME_DELIMITER", "/");
define("FIELDVALUE_DELIMITER", "_");

class ApisHRMasterController extends Controller
{
    //
    private function set_hrmaster_dates($object, $hrmaster_id, $dateobj, $generated_at){
        // Log::debug(print_r($dateobj, True));
        $object->h_r_master_update_id = $hrmaster_id;
        $object->valid_from = $dateobj['veljaOd'];
        $object->valid_to = $dateobj['veljaDo'];
        $object->changed_at = $dateobj['datumSpremembe'];
        $object->generated_at = $generated_at;
    }

    private function parseHRMasterUpdate($hrmaster_id, $data){
        $grouptypes = [
            "Ukrep" => [['statusKadrovskeStevilke']],
            "OrgDodelitev" => [
                ['skupinaZaposlenih', 'podskupinaZaposlenih'],
                ['glavnoStroskovnoMesto_Id'],
                ['glavnoStroskovnoMesto'],
                ['glavnaOrganizacijskaEnota_Id'],
                ['glavnaOrganizacijskaEnota'],
                ['glavnaOrganizacijskaEnota_kn'],
                ['glavnoDelovnoMesto_Id'],
                ['glavnoDelovnoMesto'],
                ['glavnoDelovnoMesto_kn'],
            ],
            "Razporeditev" => [
                ['organizacijskaEnota_Id'],
                ['sistemiziranoMesto'],
                ['sistemiziranoMesto_kn'],
                ['delovnoMesto_Id'],
                ['delovnoMesto_kn'],
                ['delovnoMesto'],
                ['mirovanje'],
                ['suspenz'],
            ],
            "Kandidat" => [],
            "Habilitacija" => [
                ['habilitacijskiNaziv'],
                ['habilitacijskoPodrocje'],
                ['habilitacijskoPodpodrocje'],
                ['staroHabilitacijskoPodrocje'],
                ['staroHabilitacijskoPodpodrocje'],
            ],
            "Naziv" => [['naziv']],
            "Izobrazba" => [
                ['klasiusP'],
                ['klasiusSRV'],
                ['poklicSKP8'],
                ['izobrazbaGlavna_Id'],
            ],
            "Registracija" => [],
            "OsnovnaPogodba" => [
                ['tipPogodbe'],
                ['vrstaPogodbe'],
                ['poskusnoDelo'],
                ['sistemiziranoMesto1'],
                ['sistemiziranoMesto2'],
                ['sistemiziranoMesto3'],
            ],
            "DodatnaPogodba" => [
                ['vrstaPogodbe'],
                ['sistemiziranoMesto1'],
                ['sistemiziranoMesto2'],
                ['sistemiziranoMesto3'],
 
            ],
            "Funkcija" => [
                ['funkcija'],
            ],
        ];
        $user_data = [
            "OsebniPodatki" => [
                "nagovor",
                "ime",
                "priimek",
                "EMSO",
                "datumRojstva",
                "jezik",
                "drzavljanstvo",
            ],
            "Naslov" => [
                "ulica",
                "hisnaStevilka",
                "dodatnaOznaka",
                "postnaStevilka",
                "nazivPoste",
                "drzava",
            ],
            "Komunikacija" => [
                "vrednostNaziv",
            ],
            "StaraKadStevilka" => [
                "staraKadrovskaStevilka",
            ],
            "Naziv" => [
                "naziv",
            ],
            "Izobrazba" => [
                "klasiusP",
                "klasiusSRV",
                "poklicSKP8",
                "izobrazbaGlavna_Id",
            ],
            "ARRS" => [
                "sifraARRS",
            ],
        ];
	    /* Get timestamp */
        if (isset($data['TimeStamp'])){
            $timestamp = new Datetime($data['TimeStamp']);
        } else {
            $timestamp = now();
        }
        /* Set user data */
	$userdata_array = array();
        $log = array();
        foreach ($user_data as $fieldname => $subfields){
            if (isset($data[$fieldname])){
                foreach($data[$fieldname] as $item){
                    $uid = $item['UL_Id'];
                    $infotip = $item['infotip'];
                    $podtip = '';
                    if (isset($item['podtip'])){
                        $podtip = $item['podtip'];
                    }
                    foreach ($item['data'] as $d) {
                        foreach ($subfields as $subfield){
                            $fieldname = join(GROUPNAME_DELIMITER,
                                [$infotip, $podtip, $subfield]);
                            if (isset($d[$subfield])){
                                $userdata = new UserData();
                                $userdata->uid = $uid;
                                $this->set_hrmaster_dates($userdata, $hrmaster_id, $d, $timestamp);
                                $userdata->property = $fieldname;
                                $userdata->value = $d[$subfield];
				// TODO disable once we get bulk inserts below to work
				$userdata->save();
                                // $userdata_array[] = $userdata->AttributesToArray();
                            }
                        }
                    }
                }
            }
	}
    /* bulk insert - disabled because of date formatting issues */
/*
	Log::debug(print_r($userdata_array, True));*/
	// UserData::insert($userdata_array);
 
	/* set group/OU membership */
	$ga_array = array();
        foreach ($grouptypes as $grouptype => $groupfields){
            if (isset($data[$grouptype])) {
                foreach ($data[$grouptype] as $item){
                    if (!isset($item["data"])){
                        continue;
                    }
                    $uid = $item['UL_Id'];
                    foreach ($item["data"] as $d){
                        foreach ($groupfields as $fieldarray){
                            /* fill group assignments */
                            $valarray = array();
                            foreach ($fieldarray as $field){
                                if (isset($d[$field])){
                                    $valarray[] = $d[$field];
                                } 
                            };
                            if (count($valarray) != count($fieldarray)){
                                continue;
                            }
                            $fieldname = join(FIELDNAME_DELIMITER, $fieldarray);
                            $ga = new GroupAssignment();
                            $ga->uid = $uid;
                            $this->set_hrmaster_dates($ga, $hrmaster_id, $d, $timestamp);
                            $ga->grouptype = $grouptype 
                                . FIELDNAME_DELIMITER 
                                . $fieldname;
			    $ga->group = join(GROUPNAME_DELIMITER, $valarray);
			    // $ga_array[] = $ga->attributesToArray();
                            $ga->save();
                        }
                    }
                }
            }
	}/*
		GroupAssignment::insert($ga_array);*/
        /* create OUs */
        if (isset($data['OE'])){
            foreach($data['OE'] as $item){
                $uid = $item['OE_Id'];
                foreach($item['data'] as $d){
                    $ou = new OUData();
                    $ou->uid = $uid;
                    $this->set_hrmaster_dates($ou, $hrmaster_id, $d, $timestamp);
                    $ou->OU = $d['organizacijskaEnota'];
                    $ou->save();
                }
            }
        }
        if (isset($data['NadrejenaOE'])){
            foreach($data['NadrejenaOE'] as $item){
                $child_uid = $item['OE_Id']; 
                foreach($item['data'] as $d){
                    $ou_rel = new OURelation();
                    $this->set_hrmaster_dates($ou_rel, $hrmaster_id, $d, $timestamp);
                    $ou_rel->child_uid = $child_uid;
                    $ou_rel->parent_uid = $d['id'];
                    $ou_rel->save();
                }
            }
        }
        return $log;
    }

    public function update(Request $request)
    {
        $hrmaster = new HRMasterUpdate();
        $data = $request->post();
        $hrmaster->data = json_encode($data);
        $hrmaster->save();
        
        try {
            return $this->parseHRMasterUpdate($hrmaster->id, $data);
        // Validate the value...
        } catch (Throwable $e) {
            return response(['Error' => $e], 406);
        }
    }

    public function list(Request $request)
    {
        $res = array();
        foreach (HRMasterUpdate::all() as $record){
            $res[] = json_decode($record->data);
        }
        return $res;
    }

    public function show(Request $request)
    {
        return (["Tole", "Je", "Rezultat"]);
    }

}
