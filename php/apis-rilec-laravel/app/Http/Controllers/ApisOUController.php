<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\OUData;
use App\OURelation;

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

    public function tree_index(Request $request, $date){
        $ous = array();
        $assignments = $this->index($request, $date);
        foreach($assignments as $assignment){
            if (!isset($ous[$assignment->uid])){
                $ou = new OU;
                $ou->name = $assignment->OU;
                $ou->uid = $assignment->uid;
                $ou->children = array();
                $ous[$assignment->uid] = $ou;
            }
        }
        $is_child = array();
        $last_child_uid = Null;
        foreach ($this->parent_index($date)->get() as $relation){
            $child_uid = $relation->child_uid;
            if ($last_child_uid != $child_uid){
                $parent_uid = $relation->parent_uid;
                if (isset($ous[$parent_uid]) && isset($ous[$child_uid])){
                    $parent = $ous[$relation->parent_uid];
                    $parent->children[] = $ous[$child_uid];
                    $is_child[$child_uid] = True;
                    $last_child_uid = $child_uid;
                }
            }
        }
        $tree = array();
        foreach($ous as $uid => $ou){
            if (!isset($is_child[$uid])){
                $tree[] = $ou;
            }
        }
        return $tree;
    }

    public function index(Request $request, $date = Null){
        $assignments = [];
        $last_assignment = Null;
        if (is_null($date)) {
            $date = Carbon::now();
        }
        foreach(OUData::whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->orderBy('uid')
            ->orderBy('changed_at')
            ->orderBy('updated_at')
            ->get() 
        as $assignment){
            if ($assignment->uid != $last_assignment){
                $assignments[] = $assignment;
                $last_assignment = $assignment->uid;
            }
        }
        return $assignments;
    }
}
