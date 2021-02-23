<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\OUData;
use App\OURelation;
use App\UserData;
use App\GroupAssignment;

use Carbon\Carbon;

class OU {
    public $name;
    public $uid;
    public $children = Null;
}

class ApisOUController extends Controller
{
    //
    public function show(Request $request, $date, $id){
        return OUData::where('uid', $id)
            ->whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->orderBy('changed_at')
            ->orderBy('updated_at')
            ->first();
    }

    private function parent_index($date){
        return OURelation::whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->orderBy('child_uid')
            ->orderBy('parent_uid')
            ->orderBy('changed_at')
            ->orderBy('updated_at');
    }

    public function show_parent($date, $id){
        return $this->parent_index($date)->where('child_uid', $id)
            ->first();
    }

    private function _tree_index(Request $request, $date = Null, $get_users = False){
        if (is_null($date)) {
            $date = Carbon::now();
        }
        $ous_by_uid = array();
        $ous = $this->index($request, $date);
        foreach($ous as $oudata){
            if (!isset($ous_by_uid[$oudata->uid])){
                $ou = new OU;
                $ou->OU = $oudata->OU;
                $ou->uid = $oudata->uid;
                $ou->children = array();
                $ous_by_uid[$oudata->uid] = $ou;
            }
        }
        if ($get_users){
            foreach($ous_by_uid as $ou){
                $ou->users=array();
            }
            $last_uid = Null;
            $assignments = GroupAssignment::where('grouptype', 'OrgDodelitev/glavnaOrganizacijskaEnota_Id')
                ->whereDate('valid_from', '<=', $date)
                ->whereDate('valid_to', '>=', $date)
                ->orderBy('uid')
                ->orderBy('changed_at')
                ->orderBy('generated_at')
                ->get();
            foreach($assignments as $userassignment){
                if ($userassignment->uid != $last_uid){
                    if (isset($ous_by_uid[$userassignment->group])){
                        $ous_by_uid[$userassignment->group]->users[] = $userassignment->uid;
                        $last_uid = $userassignment->uid;
                    }
                }
            }
        }
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
        $tree = array();
        foreach($ous_by_uid as $uid => $ou){
            if (!isset($is_child[$uid])){
                $tree[] = $ou;
            }
        }
        return $tree;
    }

    public function tree_index(Request $request, $date = Null){
        return $this->_tree_index($request, $date, False);
    }
    public function user_tree_index(Request $request, $date = Null){
        return $this->_tree_index($request, $date, True);
    }
    public function index(Request $request, $date = Null){
        $ous = [];
        $last_ou = Null;
        if (is_null($date)) {
            $date = Carbon::now();
        }
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
        return $ous;
    }
}
