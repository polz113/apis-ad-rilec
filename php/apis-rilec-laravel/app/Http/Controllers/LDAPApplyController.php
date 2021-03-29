<?php

namespace App\Http\Controllers;

use App\LDAPApply;
use App\LDAPApplyLog;
use App\ADDataset;
use Illuminate\Http\Request;

use Illuminate\Support\Facades\Log;


class LDAPApplyController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index()
    {
        $res = new StreamedResponse(function(){
            $handle = fopen('php://output', 'w');
            fwrite($handle, '[');
            $first = True;
            foreach (LDAPApply::cursor() as $record){
                if (!$first) fwrite($handle, ',');
                fwrite($handle, $record->data);
                $first = False;
            }
            fwrite($handle, ']');
            fclose($handle);
        });
        return $res;
    }

    private static function toletters($s, $delim = ""){
        $s = strtolower(iconv('UTF-8', 'ASCII//TRANSLIT', $s));
        $s = preg_replace("/[^a-z]+/", $delim, $s);
        $p = preg_quote($delim);
        return preg_replace("/${p}+/", "${delim}", $s);
    }

    private static function create_short_name($data){
        $name = self::toletters($data['givenName'][0]);
        $surname = self::toletters($data['sn'][0]);
        return $name . $surname[0];
    }

    private static function create_long_name($data){
        $name = implode(" ", $data['givenName']);
        $surname = implode(" ", $data['sn']);
        return self::toletters($name . " " . $surname, ".");
    }

    private static function get_ad_users($ds, $base_dn){
        /* get users from AD */
        
        $res = ldap_search($ds, $base_dn, "(&(objectclass=user)(objectcategory=person))", ["employeeId", "samAccountName", "userPrincipalName"]);
        $users_by_id = array();
        $users_by_username = array();
        $entries = ldap_get_entries($ds, $res);
        if (!$entries['count']){
            return [[],[]];
        }
        foreach ($entries as $entry) {
            if (!is_array($entry)) continue;
            if (isset($entry["employeeid"])){
                $users_by_id["employeeid"] = $entry["dn"];
            }
            Log::debug(print_r(["u:", $entry], True));
            $users_by_username[$entry["samaccountname"][0]] = $entry;
        }
        return [$users_by_id, $users_by_username];
        /*  */
    }

    private function create_or_update_user($ds, $uid, $userdata, $users_by_id, $users_by_username){
        [$user, $default_ou] = $userdata;
        if (array_key_exists($uid, $users_by_id)){
            $user_dn = $users[$uid];
        } else {
            switch(env('APIS_LDAP_DEFAULT_USERNAME_FORMAT')){
            case "short":
                $username = self::create_short_name($user);
                break;
            case "long":
            default:
                $username = self::create_long_name($user);
            }
            $i = 1;
            $s = $username;
            while(array_key_exists($s, $users_by_username)){
                $s = $username . $i;
                $i += 1;
            }
            $username = $s;
            Log::debug(print_r(["  username:", $s], True));
            $cn = implode(" ", $user['givenName']) . " " . implode(" ", $user["sn"]);
            $user_dn = "cn=" . ldap_escape($cn,"",LDAP_ESCAPE_DN) . ',' .$default_ou;
            Log::debug(print_r(["  dn:", $user_dn], True));
            $createdata = [
                // TODO pick correct class
                "objectClass" => ["top", "person", "organizationalPerson", "user"],
                "samaccountname" => [$username],
                "distinguishedname" => $user_dn,
                // TODO set correct cn
                "cn" => [$cn],
            ];
            ldap_add($ds, $user_dn, $createdata);
        }
        ldap_mod_add($ds, $user_dn, $userdata);
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create($id)
    {
        $dataset = ADDataset::findOrFail($id);
        $a = new LDAPApply();
        $a->dataset_id = $dataset->id;
        $a->save();
        /* initialize LDAP connection */
        $ds = ldap_connect(env('APIS_LDAP_URI'));
        Log::debug(print_r(["Conn:", env('APIS_LDAP_URI'), $ds], True));
        ldap_set_option($ds, LDAP_OPT_PROTOCOL_VERSION, 3);
        if (!env('APIS_LDAP_DISABLE_STARTTLS')){
            ldap_start_tls($ds);
        }
        if (env('APIS_LDAP_REFERRALS')){
            ldap_set_option($ds, LDAP_OPT_REFERRALS, 1);
        } else {
            ldap_set_option($ds, LDAP_OPT_REFERRALS, 0);
        }
        $bind_dn = env('APIS_LDAP_BIND_DN');
        if ($bind_dn){
            $res = ldap_bind($ds, $bind_dn, env('APIS_LDAP_BIND_PASSWORD'));
            Log::debug(print_r(["bind:", $res, $bind_dn, env('APIS_LDAP_BIND_PASSWORD')], True));
        }
        [$users_by_id, $users_by_username] = self::get_ad_users($ds, env('APIS_LDAP_BASE_DN'));
        foreach ($dataset->ldapactions()->orderBy('id')->cursor() as $action) {
            // $ldlog = new LDAPApplyLog();
            // $ldlog->apply = $a;
            $data = unserialize($action->data);
            $target = $action->target;
            Log::debug(print_r(["action", $action->command, $target], True));
            try {
                switch($action->command){
                case "add":
                    /* */
                    $data["DistinguishedName"] = $target;
                    ldap_add($ds, $target, $data);
                    break;
                case "mod_del":
                    ldap_mod_del($ds, $target, $data);
                    break;
                case "add_or_modify_apisuser":
                    Log::debug(print_r(["command", $action->command, $target, $data], True));
                    self::create_or_update_user($ds, $target, $data, $users_by_id, $users_by_username);
                    break;
                }
            } catch (\Exception $e){
                Log::debug(print_r(["command", $action->command, $target, $data], True));
                Log::debug(print_r(["exception", $e->getMessage()], True));
                // $ldlog->error = print_r($e, True);
            }
            // $ldlog->save();
        }
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request)
    {
        //
    }

    /**
     * Display the specified resource.
     *
     * @param  \App\LDAPApply  $lDAPApply
     * @return \Illuminate\Http\Response
     */
    public function show(LDAPApply $lDAPApply)
    {
        
    }

}
