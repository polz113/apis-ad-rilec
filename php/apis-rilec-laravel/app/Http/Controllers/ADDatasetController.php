<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\ADDataset;
use App\OUData;
use App\OURelation;
use App\UserData;
use App\LDAPApply;
use App\LDAPAction;
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
        # "2300" => ["fri1", "uni-lj", "si"],
        "2300" => ["test", "fri", "uni", "lj", "si"],
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
            "" => ["Izredni"],
        ],
        Null => ["Zunanji"],
    ],
    /* this is magically replaced by the OU hierarchy */
    "OE_MAP" => [
        "UL FRI" => "",
        "TAJ" => "Tajnistvo",
        Null => Null,
    ],
]);

define("USER_TRANSLATION_RULES", [
    # "gn" => "|OsebniPodatki.0002.0.ime",
    "givenName" => "|OsebniPodatki.0002.0.ime",
    "sn" => "|OsebniPodatki.0002.0.priimek",
    "userPrincipalName" => "|Komunikacija.0105.9007.vrednostNaziv",
    "employeeID" => "|uid",
    "telephoneNumber" => "|Komunikacija.0105.0020.vrednostNaziv",
    // "sAMAccountName" => ":get_sam_account_name" # Komunikacija.0105.9007.vrednostNaziv"], stripdomain]],
    "company" => "|KadrovskiPodatki.0.0.clanica_Id clanica_ime",
    "mail" => "|Komunikacija.0105.0010.vrednostNaziv",
    "physicalDeliveryOfficeName" => "|Komunikacija.0105.9005.vrednostNaziv",
]);

define("GROUP_TRANSLATION_RULES", [
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"],
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'Users",
            // "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota_Id OE_MAP",
            // "|OrgDodelitev.0001.0.skupinaZaposlenih,OrgDodelitev.0001.0.podskupinaZaposlenih vrste_zaposlenih",
        ],
        "default OU"
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtopravice",
            "'dodelitev",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota_Id OE_MAP",
            "|OrgDodelitev.0001.0.skupinaZaposlenih,OrgDodelitev.0001.0.podskupinaZaposlenih vrste_zaposlenih",
        ],
        "global security",
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtopravice",
            "'neznane_skupine",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota",
        ],
        "global security",
    ],

    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtopravice",
            "'oddelki",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota_Id OE_MAP",
        ],
        "global security",
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtopravice",
            "'zaposlitev",
            "|OrgDodelitev.0001.0.skupinaZaposlenih,OrgDodelitev.0001.0.podskupinaZaposlenih vrste_zaposlenih",
        ],
        "global security",
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtopravice",
            "'razporeditev",
            "|OrgDodelitev.0001.0.glavnaOrganizacijskaEnota_Id OE_MAP",
        ],
        "global security",
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtopravice", 
            "'habilitacije",
            "|Habilitacija.2003.9004.habilitacijskoPodrocje,Habilitacija.2003.9004.habilitacijskoPodpodrocje habilitacijska_podrocja",
            "|Habilitacija.2003.9004.habilitacijskiNaziv habilitacijski_naziv"
        ],
        "global security",
    ],
    [
        ["|KadrovskiPodatki.0.0.clanica_Id clanica_domena"], 
        [
            "|KadrovskiPodatki.0.0.clanica_Id clanica_prefix", "'avtomaili",
            "'delovnamesta",
            "|Razporeditev.1001.B008.delovnoMesto"
        ],
        "global distribution", # distribution group
    ]
]);

function clean($data){
    // TODO improve this
    if (is_string($data)){
        return $data;
    }
    return $data;
}

function translate($data, $translation_table, $fallback = Null){
    // Log::debug(print_r(["trans data", $data], True));
    // Log::debug(print_r(["trans table", $translation_table], True));
    if (is_array($data)) {
        $key = $data[0];
    } else {
        $key = $data;
    }
    // Log::debug(print_r(["trans key", $key], True));
    if (!array_key_exists($key, $translation_table)){
        if (array_key_exists("", $translation_table)){
            $default = $translation_table[""];
            // Log::debug(print_r(["  has default", $default], True));
            if (!is_null($default)){
                return $default;
            } else {
                // Log::debug(print_r(["  cleaning", $data], True));
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

	    return $dataset;
    }

    public function index(Request $request){
        return ADDataset::get();
    } 
    
    private function get_ou_dict($timestamp, $trans_table){
        $ou_names = array();
        $last_ou = Null;
        $parents = array();
        foreach(OUData::whereDate('valid_from', '<=', $timestamp)
            ->orderBy('uid')
            ->orderBy('generated_at', 'desc')
            ->orderBy('updated_at', 'desc')
            ->orderBy('changed_at', 'desc')
            ->cursor() as $oudata) 
        {
            if ($oudata->uid != $last_ou){
                $last_ou = $oudata->uid;
                if ($oudata->valid_to >= $timestamp){
                    $ou_name = translate($oudata->short_OU, $trans_table);
                    $ou_names[$last_ou] = $ou_name;
                }
            }
        }
        foreach(OURelation::whereDate('valid_from', '<=', $timestamp)
            ->orderBy('child_uid')
            ->orderBy('generated_at', 'desc')
            ->orderBy('changed_at', 'desc')
            ->orderBy('updated_at', 'desc')
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
                if ($ou_names[$i]){
                    array_unshift($line, $ou_names[$i]);
                }
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

    public static function to_dn($domain, $ous, $cn = Null){
        // Log::debug(print_r(["d, o, c", $domain, $ous, $cn], True));
        $dc_s = "DC=". implode(",DC=", array_map('self::ldesc', $domain));
        $ou_s = "";
        $cn_s = ""; 
        if (sizeof($ous)){
            $ou_s = "OU=". implode(",OU=", array_reverse(array_map('self::ldesc', $ous))) . ",";
        }
        if (!is_null($cn)){
            $cn_s = "CN=" . self::ldesc($cn) . ",";
        }
        return $cn_s . $ou_s . $dc_s;
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
        $trans_dicts["OE_MAP"] = $this->get_ou_dict($timestamp, $trans_dicts["OE_MAP"]);
        /* convert original groups to actual ones */
        // Log::debug(print_r(["RULES", $trans_dicts], True));
        $userdata = UserData::properties_at_timestamp($timestamp);
        $groups = array();
        $needed_ous = array();
        $users = array();
        $users_hrmu = array();
        foreach ($userdata as $user) {
            /* make uid look like a normal dataitem */
            $uid = $user["uid"];
            $user["uid"] = ["uid" => $uid];
            // Log::debug(print_r(["user", $user], True));
            /* user properties */
            $ad_user = array();
            /* hrm updates the properties were based on */
            $ad_user_hrmu = array();
            $default_user_ou = array();
            $memberof = array();
            $memberof_hrmu = array();
            foreach (GROUP_TRANSLATION_RULES as $rules) {
                [$domainrules, $ourules, $grouptype] = $rules;
                foreach($user as $dataitem => $data) {
                    $domain = self::assemble_from_rules($data, $domainrules, $trans_dicts);
                    if ($domain != Null) {
                        break;
                    }
                }
                if (!isset($domain)) continue;
                foreach($user as $dataitem => $data) {
                    // Log::debug(print_r(["ddata:", $data], True));
                    $ous_and_cn = self::assemble_from_rules($data, $ourules, $trans_dicts);
                    // Log::debug(print_r(["ouc:", $ous_and_cn], True));
                    if ($ous_and_cn != Null){
                        $ou_tmp = [];
                        $cn = array_slice($ous_and_cn, -1)[0];
                        $ous = array_slice($ous_and_cn, 0, -1);
                        foreach ($ous as $ou) {
                            $ou_tmp[] = $ou;
                            $needed_ous[self::to_dn($domain, $ou_tmp)] = True;
                        }
                        /* turn array into DN */
                        if ($grouptype == "default OU"){
                            $default_ou = self::to_dn($domain, $ous_and_cn);
                            if (sizeof($ous_and_cn) > 0){
                                $needed_ous[$default_ou] = True;
                            }
                            $default_user_ou = $default_ou;
                        } else {
                            $group_dn = self::to_dn($domain, $ous, $cn);
                            $groups[$group_dn] = [$grouptype, $dataitem];
                            $memberof[] = $group_dn;
                            $memberof_hrmu[] = $dataitem;
                        }
                    }
                }
            }
	        // Log::debug(print_r([$objname, $hritem], True));
            /* Map original user properties to AD data */
            foreach ($user as $dataitem => $data) {
                foreach (USER_TRANSLATION_RULES as $property => $rule){
                    try {
                        $ad_user[$property] = [translate_by_rule($data, $rule, $trans_dicts)[0]];
                        $ad_user_hrmu[$property] = $dataitem;
                    } catch (Exception $e) {
                        // Log::debug(print_r(["e", $e->getMessage()], True));
                    };
                }
            }
            $ad_user['MemberOf'] = $memberof;
            $users_hrmu[$uid] = array_merge($ad_user_hrmu, $memberof_hrmu);
            // Log::debug(print_r(["AD user", $ad_user], True));
            /* add create-or-update for users */
            $users[$uid] = [$ad_user, $default_user_ou];
            /* add every memberof for each user */
        }
        /* prune needed_ous */
        $needed_ous = array_keys($needed_ous);
        sort($needed_ous);
        /* create actions in the database */
        /* Create OUs for the groups */
        foreach($needed_ous as $gou){
            $action = new LDAPAction();
            $action->dataset_id = $dataset->id;
            $action->command = "add";
            $data = array();
            $data["objectClass"] = ["top", "organizationalUnit"];
            $action->target = $gou;
            $action->data = serialize($data);
            $action->save();
        }
        /* Create groups */
        foreach ($groups as $group_dn => $gti){
            $grouptype = $gti[0];
            if ($grouptype == "default OU") continue;
            [$hrmu_id, $dataitem] = explode(".", $gti[1]);
            $action = new LDAPAction();
            $action->dataset_id = $dataset->id;
            $action->command = "add";
            $action->target = $group_dn;
            $data = array();
            $data['objectClass'] = ["top", "group"];
            // $data['cn'] = $cn; TODO: check if this is neccessarry
            /* set correct type for AD groups */
            switch ($grouptype){
                case "local distribution":
                    $gt = 0x4;
                    break;
                case "universal distribution":
                    $gt = 0x8;
                    break;
                case "global distribution":
                case "distribution":
                    $gt = 0x2;
                    break;
                case "local security":
                    $gt=0x80000004;
                    break;
                case "universal security":
                    $gt=0x80000008;
                    break;
                case "global security":
                case "security":
                default:
                    $gt=0x80000002;
                    break;
            }
            $data['groupType'] = $gt;
            $action->data = serialize($data);
            $action->save();
        }
        /* $group = 'CN=mygroup,OU=myOU,DC=mydomain,DC=com';

$group_info['member'] = 'CN=User\, Test,CN=Users,DC=mydomain,DC=com';

ldap_mod_del($ldap, $group, $group_info);*/
        /* Clear members for groups */
        foreach ($groups as $group_dn => $gti){
            $grouptype = $gti[0];
            // [$hrmu_id, $dataitem] = explode(".", $gti[1]);
            $action = new LDAPAction();
            $action->dataset_id = $dataset->id;
            $action->command = "mod_del";
            $action->target = $group_dn;
            $data['member'] = [];
            /* 
            $add['objectclass'] = 'organizationalRole'; #this is a required attribute for a group
            $add['cn'] = 'NewGroup'; #give any name
            if(ldap_add($ds, $dn, $add)) echo "group ".$add['cn']." successfully added to ".$dn;
             * */
            $action->data = serialize($data);
            $action->save();
        }
        /* Set user properties */
        foreach ($users as $uid => $data){
            /* foreach ($users_hrmu[$uid] as $property => $hdi){
                [$hrmu_id, $dataitem] = explode(".", $hdi);
            }*/
            $action = new LDAPAction();
            $action->dataset_id = $dataset->id;
            $action->target = $uid;
            $action->command = "add_or_modify_apisuser";
            $action->data = serialize($data);
            $action->save();
        }
        /* >>> ldap_mod_del($ds, $groupdn[0], ["member"=>[]])
=> true
>>> ldap_mod_add($ds, $groupdn[0], ["member" => [$polzdn]])
=> true
>>> ldap_mod_del($ds, $groupdn[0], ["member"=>[]])
         
         */
        return($dataset);
    }
}
