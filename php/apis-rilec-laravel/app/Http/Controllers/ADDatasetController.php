<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\ADDataset;
use App\OUData;
use App\OURelation;
use App\UserData;
use Carbon\Carbon;
use Exception;

use Illuminate\Support\Facades\Log;

function only_alnum($data){
    return preg_replace("/[^a-zA-Z0-9]+/", "", $data);
}

function pass($data){
    return $data;
};

define("TRANSLATION_TABLE", [
    # "OE_MAP" => magicno ustvarjen v get_ou_dict
    "clanica_domena" => [
        "2300" => ["fri1", "uni-lj", "si"],
    ],
    "clanica_prefix" => [
        "2300" => ["FRI"],
    ],
    "clanica_ime" => [
        "2300" => ["Fakulteta za računalništvo in informatiko"],
    ],
    "habilitacijska_podrocja" => [
        "001" => [
            "00" => ["Test1"],
        ],
        "002" => [
            "00" => ["Test2"],
        ],
        "019" => [ 
            "00" => ["Test3"],
        ]
    ],
    "habilitacijski_naziv" => [
        "11" => ["TEST1sistent"],
        "12" => ["TEST2sistent"],
        "13" => ["TEST3sistent"],
        "31" => ["TEST5sistent"],
        "41" => ["TEST4sistent"],
    ],
    "vrste_zaposlenih" => [
        "1" => [ 
            "11" => ["Redni"],
            "" => ["Izedni"],
        ],
        Null => ["Zunanji"],
    ]
]);

define("USER_TRANSLATION_RULES", [
    "gn" => "|OsebniPodatki.0002.0.ime",
    "givenName" => "|OsebniPodatki.0002.0.ime",
    "sn" => "|OsebniPodatki.0002.0.priimek",
    "userPrincipalName" => "|Komunikacija.0105.9007.vrednostNaziv",
    "employeeID" => "|uid",
    "telephoneNumber" => "|Komunikacija.0105.0020.vrednostNaziv",
    // "sAMAccountName" => ":get_sam_account_name" # Komunikacija.0105.9007.vrednostNaziv"], stripdomain]],
    "company" => "|KadrovskiPodatki.0.0.clanica_Id clanica_ime",
    "mail" => "|Komunikacija.0105.0010.vrednostNaziv",
    "physicalDeliveryOffice" => "|Komunikacija.0105.9005.vrednostNaziv",
]);

define("GROUP_TRANSLATION_RULES", [
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtomatika",
            "'dodelitev",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota_Id OE_MAP",
            "|OrgDodelitev.0001.0.skupinaZaposlenih,OrgDodelitev.0001.0.podskupinaZaposlenih vrste_zaposlenih",
        ],
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtomatika",
            "'neznane_skupine",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota",
        ],
    ],

    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtomatika",
            "'oddelki",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota_Id OE_MAP",
        ],
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtomatika",
            "'zaposlitev",
            "|OrgDodelitev.0001.0.skupinaZaposlenih,OrgDodelitev.0001.0.podskupinaZaposlenih vrste_zaposlenih",
        ],
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtomatika",
            "'razporeditev",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota_Id OE_MAP",
        ],
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix",
            "'avtomatika", "'habilitacije",
            "|Habilitacija.2003.9004.habilitacijskoPodrocje,Habilitacija.2003.9004.habilitacijskoPodpodrocje habilitacijska_podrocja",
            "|Habilitacija.2003.9004.habilitacijskiNaziv habilitacijski_naziv"
        ]
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtomatika",
            "'delovnamesta",
            "|Razporeditev.1001.B008.delovnoMesto"
        ]
    ]
]);

function clean($data){
    // TODO improve this
    return $data;
}

function translate($data, $translation_table, $fallback = Null){
    // Log::debug(print_r(["trans data", $data], True));
    if (is_array($data)) {
        $key = $data[0];
    } else {
        $key = $data;
    }
    // Log::debug(print_r(["trans key", $key], True));
    if (!array_key_exists($key, $translation_table)){
        if (isset($translation_table[""])){
            $default = $translation_table[""];
            if (!is_null($default)){
                return $default;
            } else {
                return clean($data);
            }
        }
        if ($fallback != Null) {
            return $fallback($data);
        }
        return Null;
    }
    if (is_array($data) && sizeof($data) > 1){
        return translate(array_slice($data, 1), $translation_table[$key]);
    }
    return $translation_table[$key];
}



function translate_by_rule($data, $rule, $tables, $fallback = Null){
    if ($rule == "") return "";
    switch ($rule[0]){
        case "'":
            return [ substr($rule, 1) ];
            break;
        case "|":
            // Log::debug(print_r(["data", $data], True));
            $keyspec = strtok(substr($rule, 1), " ");
            $trans_name = strtok(" ");
            if ($trans_name){
                $trans = $tables[$trans_name];
            }
            $key_array = [];
            $key = strtok($keyspec, ",");
            do {
                $key_array[] = $data[$key];
            } while($key = strtok(","));
            // Log::debug(print_r(["key_array", $key_array], True));
            if (isset($trans)){
                $res = translate($key_array, $trans, $fallback);
            } else {
                return $key_array;
                // TODO: make sure the fallback works
                return $fallback($key_array);
            }
            // Log::debug(print_r(["result:", $res], True));
            return $res;
            break;
        default:
            return $rule;
    }
}


class ADDatasetController extends Controller
{
    public function show(Request $request, $id){
	    $dataset = ADDataset::where('id', $id)->first();
	    return $dataset->toArray();
    }

    public function index(Request $request){
        return ADDataset::get();
    }
    
    public function remap_userdata($orig_data){
    
    }
    
    private function get_ou_dict($timestamp){
        $ou_names = array();
        $last_ou = Null;
        $parents = array();
        foreach(OUData::whereDate('valid_from', '<=', $timestamp)
            ->orderBy('uid')
            ->orderBy('changed_at')
            ->orderBy('updated_at')
            ->cursor() as $oudata) 
        {
            if ($oudata->uid != $last_ou){
                $last_ou = $oudata->uid;
                if ($oudata->valid_to >= $timestamp){
                    $ou_names[$last_ou] = $oudata->short_OU;
                }
            }
        }
        foreach(OURelation::whereDate('valid_from', '<=', $timestamp)
            ->orderBy('child_uid')
            ->orderBy('changed_at')
            ->orderBy('updated_at')
            ->cursor() as $ourelation)
        {
            if ($ourelation->child_uid != $last_ou){
                $last_ou = $ourelation->child_uid;
                if ($oudata->valid_to >= $timestamp){
                    $parents[$last_ou] = $ourelation->parent_uid;
                }
            }
        }
        $ou_dict = array();
        foreach($ou_names as $uid => $name){
            $prev_uids = [];
            $line = [];
            $i = $uid;
            do {
                array_unshift($line, $ou_names[$i]);
                $prev_uids[$uid] = True;
                $i = $parents[$i];
            } while (isset($ou_names[$i]) && !array_key_exists($i, $prev_uids));
            $ou_dict[$uid] = $line;
        }
        return $ou_dict;
    }

    private static function ldesc($x){
        return ldap_escape($x, "", LDAP_ESCAPE_DN);
    }

    public static function to_dn($domain, $ous, $cn){
        // Log::debug(print_r(["d, o, c", $domain, $ous, $cn], True));
        $dc_s = "DC=". implode(", DC=", array_map('self::ldesc', $domain));
        $ou_s = "OU=". implode(", OU=", array_map('self::ldesc', $ous));
        return $dc_s . ", " . $ou_s . ", " . "CN=" . self::ldesc($cn);
    }

    private function assemble_from_rules($data, $rules, $trans_dicts){
        $res = [];
        $to_join = array();
        foreach ($rules as $rule){
            // Log::debug(print_r(["Rule:", $rule], True));
            try {

                $new_components = translate_by_rule($data, $rule, $trans_dicts);
                // Log::debug(print_r(["  adding", $new_components], True));
                if (!is_null($new_components)) {
                    $to_join = array_merge($to_join, $new_components);
                } else {
                    throw new Exception("Translate failed");
                }
            } catch (Exception $e){
                // Log::debug(print_r(["de", $e->getMessage()], True));
                return Null;
            }
        }
            // if (sizeof($to_join) > 0) $res[] = $to_join;
       
        // Log::debug(print_r(["  returning", $to_join], True));
        return $to_join;
    }

    public function create(Request $request, $timestamp = Null){
        if (is_null($timestamp)) {
            $timestamp = Carbon::now();
        }
        $dataset = new ADDataset();
        $dataset->save();
        /* fill groups */
        $log = array();
        $trans_dicts = TRANSLATION_TABLE;
        $trans_dicts["OE_MAP"] = $this->get_ou_dict($timestamp);
        /* convert original groups to actual ones */
        // Log::debug(print_r(["RULES", $trans_dicts], True));
        $userdata = UserData::properties_at_timestamp($timestamp);
        $groups = array();
        $users = array();
        foreach ($userdata as $user) {
            /* make uid look like a normal dataitem */
            $user["uid"] = ["uid" => $user["uid"]];
            // Log::debug(print_r(["user", $user], True));
            $ad_user = array();
            $group_ous_and_cns = [];
            foreach (GROUP_TRANSLATION_RULES as $rules) {
                $domains = [];
                foreach($user as $dataitem => $data) {
                    $domain = self::assemble_from_rules($data, $rules[0], $trans_dicts);
                    if ($domain != Null) {
                        $domains[] = $domain;
                        break;
                    }
                }
                foreach($user as $dataitem => $data) {
                    // Log::debug(print_r(["ddata:", $data], True));
                    $ous_and_cn = self::assemble_from_rules($data, $rules[1], $trans_dicts);
                    // Log::debug(print_r(["ouc:", $ous_and_cn], True));
                    if ($ous_and_cn != Null){
                        $group_ous_and_cns[] = $ous_and_cn;
                    }
                }
            }
	            // Log::debug(print_r([$objname, $hritem], True));
                /* Map original user properties to AD data */
            foreach ($user as $dataitem => $data) {
                foreach (USER_TRANSLATION_RULES as $property => $rule){
                    try {
                        $ad_user[$property] = translate_by_rule($data, $rule, $trans_dicts)[0];
                    } catch (Exception $e) {
                        // Log::debug(print_r(["e", $e->getMessage()], True));
                    };
                }
            }
            $memberof = array();
            foreach ($group_ous_and_cns as $ous_and_cn) {
                // Log::debug(print_r(["OUs and CN", $ous_and_cn], True));
                $ous = array_slice($ous_and_cn, 0, -1);
                $cn = array_slice($ous_and_cn, -1)[0];
                /* turn array into DN */
                $group_dn = self::to_dn($domains[0], $ous, $cn);
                /* add DN to $groups */
                $memberof[] = $group_dn;
                // Log::debug(print_r(["DN", $group_dn], True));
            }
            $ad_user['MemberOf'] = $memberof;
            // Log::debug(print_r(["AD user", $ad_user], True));
            /* add create-or-update for users */
            $users[] = $ad_user;
            /* add create for security groups */
            /* add create for distribution groups */
            /* add clear members for groups */
            /* add every memberof for each user */
        }
        /* write groups to database */

        return($users);
    }
}
