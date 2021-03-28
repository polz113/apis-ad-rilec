<?php

namespace App\Http\Controllers;

use App\LDAPApply;
use App\ADDataset;
use Illuminate\Http\Request;

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

    private function toletters($s, $delim = ""){
        $s = $data['gn'] . ' ' . $data['sn'];
        $s = strtolower(iconv('UTF-8', 'ASCII//TRANSLIT', $s));
        $s = preg_replace("/[^a-z]+/", $delim, $s);
        $p = preg_quote($delim);
        return preg_replace("/${p}+/", "${delim}", $s);
    }

    private function create_short_name($data){
        $name = toletters($data['gn']);
        $surname = toletters($data['sn']);
        return $name[0] . $surname;
    }

    private function create_long_name($data){
        $s = self::toletters($data, ".");
        return $s;
    }

    private function get_ad_users($ds, $base_dn){
        /* get users from AD */
        $res = ldap_search($ds, $base_dn, "(&(objectclass='top',objectclass='person',objectclass='organizationalPerson',objectclass='user'))", ["employeeId"]);
        $users = array();
        foreach (ldap_get_entries($res) as $entry) {
            if (isset($entry["employeeid"])){
                $users["employeeid"] = $entry["dn"];
            }
        }
        return $users;
        /*  */
    }

    private function create_or_update_user($ds, $uid, $userdata, $users){
        [$user, $default_ou] = $userdata;
        if (array_key_exists($uid, $users)){
            $user_dn = $users[$uid];
        } else {
            switch(env('APIS_LDAP_DEFAULT_USERNAME_FORMAT')){
            case "short":
                $username = create_short_name($user);
                break;
            case "long":
            default:
                $username = create_long_name($user);
            }
            $user_dn = $default_ou . "cn=" . $username;
            $createdata = [
                // TODO pick correct class
                "objectClass" = ["top", "person", "organizationalPerson", "user"],
                "samaccountname" = [$username],
                // TODO set correct cn
                "cn" = $user['gn'] . " " . $user["sn"],
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
        $dataset = ADDataset();
        $a = new LDAPApply();
        $a->dataset = $dataset;
        $a->save();
        /* initialize LDAP connection */
        $ds = ldap_connect(env('APIS_LDAP_URI'));
        $ldap_set_options($ds, LDAP_OPT_PROTOCOL_VERSION, 3);
        if (!isset(env('APIS_LDAP_DISABLE_STARTTL')) || !env('APIS_LDAP_DISABLE_STARTTL')){
            ldap_start_tls($ds);
        }
        if (isset(env('APIS_LDAP_REFERRALS')) && env('APIS_LDAP_REFERRALS')){
            $ldap_set_options($ds, LDAP_OPT_REFERRALS, 1);
        } else {
            $ldap_set_options($ds, LDAP_OPT_REFERRALS, 0);
        }
        $users = get_ad_users($ds);
        foreach ($dataset->ldapactions as $action) {
            $ldlog = new LDAPApplyLog();
            $ldlog->apply = $a;
            $data = unserialize($action->data);
            try {
                switch($action->){
                case "add":
                    /* */
                    ldap_add($ds, $target, $data);
                    break;
                case "mod_del":
                    ldap_mod_del($ds, $target, $data);
                    break;
                case "add_or_modify_ldapuser":
                    create_or_update_user($ds, $target, $data, $users);
                    break;
                }
            } catch (Exception $e){
                $ldlog->error = print_r($e, True);
            }
            $ldlog->save();
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
