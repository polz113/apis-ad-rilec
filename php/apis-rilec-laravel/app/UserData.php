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
    protected static function extract_valid_dataitems($maybe_valid, $invalid){
        $invalid_dict = array();
        // $result = array();
        foreach ($invalid as $invalid_ditem => $invalid_data){
            $invalid_dict[] = $invalid_data;
        }
        foreach($maybe_valid as $user_ditem => $user_data){
            /* if (!in_array($user_data, $invalid_dict)){
                $result[$user_ditem] = $user_data;
        }*/
            if (in_array($user_data, $invalid_dict)){
                unset($maybe_valid[$user_ditem]);
            }
            $invalid_dict[] = $user_data;
        }
        return $maybe_valid;
    }
    /* get properties as they should be at some moment in time */
    /* if the properties are changed retroactively, the results may change even for the past */
    public static function properties_at_timestamp($timestamp){ 
        $properties = UserData::whereDate('valid_from', '<=', $timestamp)
            // ->whereDate('valid_to', '>=', $date)
            ->orderBy('uid')
            ->orderBy('generated_at', 'desc')
            ->orderBy('updated_at', 'desc')
            ->orderBy('h_r_master_update_id')
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
            Log::debug(print_r(["entry", $entry->h_r_master_update_id, $entry->dataitem, $entry->property, $entry->value], True));
            /* the entries for the last users are done */
            if ($entry['uid'] != $old_uid){
                if (!is_null($old_uid)){
                    /* $user = UserData::extract_valid_dataitems(
                        $maybe_data, $invalid_data);*/
                    $user['uid'] = $old_uid;              
                    Log::debug(print_r(["Ussr", $user], True));
                    $users[] = $user;
                }
                /*
                $invalid_data = array();
                $maybe_data = array();*/
                $hrupdate = Null;
                $user = array();
                $seen_keys = array();
                $current_keys = array();
                $old_uid = $entry['uid'];
            }

            $prop = $entry['property'];
            $value = $entry['value'];
            $old_hrupdate = $hrupdate;
            $hrupdate = $entry['h_r_master_update_id'];  
            $dataitem = '' . $hrupdate . '.' . $entry['dataitem'];
            if ($hrupdate != $old_hrupdate){
                $seen_keys = array_merge($seen_keys, $current_keys);
                $current_keys = array();
            }
            if (($old_dataitem != $dataitem)){
                if (!is_null($old_dataitem) && (sizeof($data) > 0)){
                    $user[$old_dataitem] = $data;
                    $data = array();
                }
                $old_dataitem = $dataitem;
            };
            if (($entry['valid_to'] >= $timestamp) && (!array_key_exists($prop, $seen_keys))){
                $data[$prop] = $value;
            }
            $current_keys[$prop] = True;
            
            /*if ($entry['valid_to'] >= $date){
                if (!array_key_exists($dataitem, $maybe_data)) {
                    $maybe_data[$dataitem] = array();
                }
                $maybe_data[$dataitem][$prop] = $value;
            } else {
                /* find the entry to invalidate */
            /*    if (!array_key_exists($dataitem, $invalid_data)) {
                    $invalid_data[$dataitem] = array();
                }
                $invalid_data[$dataitem][$prop] = $value;
            }*/
            // Log::debug(print_r($user, True)); 
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
