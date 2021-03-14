<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\ADDataset;
use Carbon\Carbon;

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
	i   }
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
        $userdata = UserData::whereDate('valid_from', '<=', $date)
                ->whereDate('valid_to', '>=', $date)
                ->orderBy('changed_at')
                ->orderBy('generated_at')
                ->get();
        $groups = array();
        foreach($userdata as $data){
            /* map user properties to group membership */

            /* map original user properties to AD data */
        }
        foreach($groups as $group => $members){
            /* create group memberships */
        }
        /* write group to database */

        /* add users to group */

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
