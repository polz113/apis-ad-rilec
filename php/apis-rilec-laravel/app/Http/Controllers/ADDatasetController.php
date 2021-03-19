<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\ADDataset;
use Carbon\Carbon;

function translate($data, $translation_table){
    return $translation_table[$data];
}

function translate_or_pass($data, $translation_table){
    if (!array_key_exists($data, $translation_table)){
        return preg_replace("/[^a-zA-Z0-9]+/", "", $name);
    }
    return $translation_table[$data];
}

function unsafe_translate_or_pass($data, $translation_table){
    if (!array_key_exists($data, $translation_table)){
        return $data;
    }
    return $translation_table[$data];
}

define("USER_TRANSLATION_RULES", [
    "gn" => [["OsebniPodatki.0002.0.ime"], Null],
    "givenName" => [["OsebniPodatki.0002.0.ime"], Null],
    "sn" => [["OsebniPodatki.0002.0.priimek"], Null],
    "userPrincipalName" => [["Komunikacija.0105.9007.vrednostNaziv"], Null],
    "employeeID" => [["uid"], Null],
    "telephoneNumber" => [["Komunikacija.0105.0020.vrednostNaziv"], Null],
    // "sAMAccountName" => [[["Komunikacija.0105.9007.vrednostNaziv"], stripdomain]],
    "company" => [[["KadrovskiPodatki.0.0.clanica_Id"], translate_or_pass]],
    "mail" => [[["Komunikacija.0105.0010.vrednostNaziv"], Null]],
    "physicalDeliveryOffice" => [[["Komunikacija.0105.9005.vrednostNaziv"], Null]],
]);

define("TRANSLATION_TABLE", [
    "clanica_domena" => [
        "2300" => "fri1.uni-lj.si",
    ],
    "clanica_prefix" => [
        "2300" => "FRI",
    ],
    "habilitacijsko_podrocje" => [
        "001" => "Test1",
        "002" => "Test2",
        "019" => "Test3",
    ],
    "habilitacijski_naziv" => [
        "11" => "TEST1sistent",
        "12" => "TEST2sistent",
        "13" => "TEST3sistent",
        "31" => "TEST5sistent",
        "41" => "TEST4sistent",
    ]
]);

define("GROUP_TRANSLATION_RULES", [
    "laboratoriji/IME/STATUS_ZAPOSLENEGA/",
    "organigram/SKUPINA/PODSKUPINA/PODPODPODSKUPINA",
    "habilitacije/HABILITACIJA",
    "delovnamesta/MESTO",
    "{clanica_domena:KadrovskiPodatki.0.0.clanica_Id}/{clanica_prefix:KadrovskiPodatki.0.0.clanica_Id}/{}"
]);

"Habilitacija.habilitacijskiNaziv: 11";
"Habilitacija.habilitacijskiNaziv: 13";
'Habilitacija.habilitacijskoPodrocje: "001"';
'Habilitacija.habilitacijskoPodpodrocje: "00"';
'sistemiziranoMesto: "Asistent';

class ADDatasetController extends Controller
{


    public function show(Request $request, $id){
	$dataset = ADDataset::where('id', $id)->first();
	return $dataset->toArray();
    }

    public function index(Request $request){
        return ADDataset::get();
    }
    
    public function remap_group($orig_group, $trans_dicts){
    	foreach($trans_dicts as $trans_dict){
	    }
    }

    public function remap_userdata($orig_data){
    
    }
    
    private function get_oe_dict($timestamp){
        $ous = [];
        $last_ou = Null;
        foreach(OUData::whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->orderBy('uid')
            ->orderBy('changed_at')
            ->orderBy('updated_at')
            ->get() 
        as $oudata){
            if ($oudata->uid != $last_ou){
                $ous[] = $oudata;
                $last_ou = $oudata->uid;
            }
        }
    }

    public function create(Request $request, $timestamp = Null){
        if (is_null($timestamp)) {
            $timestamp = Carbon::now();
        }
        $dataset = new ADDataset();
        $dataset->save();
        /* fill groups */
        $log = array();
        $trans_dicts = array();
        $trans_dicts[] = $this->get_oe_dict($timestamp);
        /* convert original groups to actual ones */
        $userdata = UserData::properties_at_timestamp($timestamp);
        $groups = array();
        foreach($userdata as $user){
            foreach($user as $dataitem => $data)
                /* map user properties to group membership */
                
	            // Log::debug(print_r([$objname, $hritem], True));
                /* map original user properties to AD data */
            }
        }
        foreach($groups as $group => $members){
            /* create group memberships */
        }
        /* write groups to database */

        /* add users to groups */

        /* fill user data */
        foreach($ous_by_uid as $ou){
            $ou->users=array();
        }
        $last_uid = Null;

       	$is_child = array();
        $last_child_uid = Null;
        foreach ($this->parent_index($date)->get() as $relation){
            $child_uid = $relation->child_uid;
            if ($last_child_uid != $child_uid){
                $parent_uid = $relation->parent_uid;
                if (isset($ous_by_uid[$parent_uid]) && isset($ous_by_uid[$child_uid])){
                    $parent = $ous_by_uid[$relation->parent_uid];
                    $parent->children[] = $ous_by_uid[$child_uid];
                    $is_child[$child_uid] = True;
                    $last_child_uid = $child_uid;
                }
            }
        }
 
        return($log);
    }
}
