<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

use Illuminate\Support\Facades\Log;

class UserData extends Model
{
    //
    protected $dates = [ 
        'valid_from',
        'valid_to',
        'changed_at',
        'generated_at',
    ];

    /* get properties as they should be at some moment in time */
    /* if the properties are changed retroactively, the results may change even for the past */
    public static function properties_at_timestamp($timestamp){ 
        $properties = UserData::whereDate('valid_from', '<=', $timestamp)
            // ->whereDate('valid_to', '>=', $date)
            ->orderBy('uid')
            ->orderBy('generated_at', 'desc')
            ->orderBy('updated_at', 'desc')
            ->orderBy('h_r_master_update_id', 'desc')
            ->orderBy('dataitem')
            ->orderBy('changed_at', 'desc')
            ->orderBy('property')
            ->orderBy('valid_to', 'desc');
        $user = Null;
        $users = array();
        $old_uid = Null;
        $old_dataitem = Null;
        $data = array();
        foreach ($properties->cursor() as $entry){
            /* the entries for the last users are done */
            if ($entry['uid'] != $old_uid){
                if (!is_null($old_uid)){
                    /* $user = UserData::extract_valid_dataitems(
                        $maybe_data, $invalid_data);*/
                    $user['uid'] = $old_uid; 
                    // Log::debug(print_r(["Ussr", $user], True));
                    $users[] = $user;
                    unset($user);
                }
                /*
                $invalid_data = array();
                $maybe_data = array();*/
                $first_hrupdate = $entry['h_r_master_update_id'];  
                $user = array();
                $old_uid = $entry['uid'];
            }
            $hrupdate = $entry['h_r_master_update_id'];  
            $dataitem = '' . $hrupdate . '.' . $entry['dataitem'];
            if ($hrupdate != $first_hrupdate){
                continue;
            }
            if (($old_dataitem != $dataitem)){
                if (!is_null($old_dataitem) && (sizeof($data) > 0)){
                    $user[$old_dataitem] = $data;
                    unset($data);
                    $data = array();
                }
                $old_dataitem = $dataitem;
            };
            if ($entry['valid_to'] >= $timestamp){
                $prop = $entry['property'];
                $value = $entry['value'];
                $data[$prop] = $value;
            }
        }
        if ($old_uid != Null) {
            /* $user = UserData::extract_valid_dataitems(
                $maybe_data, $invalid_data); */
            $user['uid'] = $old_uid;
            $users[] = $user;
        }
        return $users;
    }
}
